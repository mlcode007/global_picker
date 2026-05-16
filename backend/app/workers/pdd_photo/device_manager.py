"""
设备池管理器 —— 设备获取、加锁、释放、心跳、异常标记。

拍照购调度：只使用「云手机池」中状态为 available 且已配置 adb_host_port 的实例；
与 device_pool 行级锁（FOR UPDATE SKIP LOCKED）配合，多任务可并行占用不同设备。

新增超时检测：当设备状态为 busy 但绑定的任务已超时（超过 TASK_TIMEOUT_MINUTES 分钟），
自动释放设备。用于处理服务器重启导致的设备卡死问题。
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Set

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.cloud_phone import CloudPhonePool
from app.models.device import Device
from app.models.photo_search_task import PhotoSearchTask
from .adb_client import AdbClient

logger = logging.getLogger(__name__)

PDD_PACKAGE = "com.xunmeng.pinduoduo"

RECOVERABLE_STATUSES = ("offline", "error")
ADB_RECONNECT_RETRIES = 2
ADB_RECONNECT_INTERVAL = 2

# 多任务抢少量设备时：在超时内轮询，避免瞬时无 idle 就立刻 NO_DEVICE
ACQUIRE_WAIT_SECONDS = 10
ACQUIRE_POLL_INTERVAL = 2.0

# 任务超时时间（分钟）- 超过此时长的任务视为卡死，自动释放设备
TASK_TIMEOUT_MINUTES = 3


class DeviceManager:

    def __init__(self, db: Session):
        self.db = db

    # ── 超时任务检测与自动释放 ────────────────────────────────

    def _check_and_release_timeout_devices(self, user_id: Optional[int] = None) -> int:
        """检查并释放超时任务绑定的设备。
        
        当设备状态为 busy 但绑定的任务已超过 TASK_TIMEOUT_MINUTES 分钟没有更新，
        或者任务已经完成（success/failed/cancelled）但设备仍显示 busy，
        自动释放设备。
        
        用于处理服务器重启或进程崩溃导致的设备卡死问题。
        
        Args:
            user_id: 可选，仅处理指定用户的设备
            
        Returns:
            释放的设备数量
        """
        released_count = 0
        timeout_threshold = datetime.now() - timedelta(minutes=TASK_TIMEOUT_MINUTES)

        # 查询所有 busy 状态的设备
        query = self.db.query(Device).filter(Device.status == "busy")
        if user_id is not None:
            # 限制只处理指定用户云手机池中的设备
            cloud_serials = self._list_cloud_pool_adb_serials(user_id)
            if cloud_serials:
                query = query.filter(Device.device_id.in_(cloud_serials))

        busy_devices = query.all()

        for device in busy_devices:
            task_id = device.current_task_id
            if not task_id:
                # 设备状态为 busy 但没有绑定任务，直接释放
                logger.warning("Device %s is busy but has no task, releasing", device.device_id)
                device.status = "idle"
                device.current_task_id = None
                device.last_heartbeat = datetime.now()
                released_count += 1
                continue

            # 查询绑定的任务
            task = self.db.query(PhotoSearchTask).filter(PhotoSearchTask.id == task_id).first()
            if not task:
                # 任务不存在，释放设备
                logger.warning("Device %s is busy but task #%d not found, releasing", 
                             device.device_id, task_id)
                device.status = "idle"
                device.current_task_id = None
                device.last_heartbeat = datetime.now()
                released_count += 1
                continue

            # 检查任务是否已完成
            if task.status in ("success", "failed", "cancelled"):
                logger.warning("Device %s is busy but task #%d is %s, releasing", 
                             device.device_id, task_id, task.status)
                device.status = "idle"
                device.current_task_id = None
                device.last_heartbeat = datetime.now()
                released_count += 1
                continue

            # 检查任务是否超时（根据任务开始时间判断）
            if task.started_at and task.started_at < timeout_threshold:
                elapsed_minutes = (datetime.now() - task.started_at).total_seconds() / 60
                logger.warning(
                    "Device %s is busy with task #%d which started %d minutes ago (timeout=%d), releasing",
                    device.device_id, task_id, int(elapsed_minutes), TASK_TIMEOUT_MINUTES
                )
                device.status = "idle"
                device.current_task_id = None
                device.last_heartbeat = datetime.now()
                released_count += 1
                continue

            # 检查设备最后心跳时间（服务器重启后心跳会停止）
            if device.last_heartbeat and device.last_heartbeat < timeout_threshold:
                elapsed_minutes = (datetime.now() - device.last_heartbeat).total_seconds() / 60
                logger.warning(
                    "Device %s heartbeat timeout: last heartbeat %d minutes ago (timeout=%d), releasing",
                    device.device_id, int(elapsed_minutes), TASK_TIMEOUT_MINUTES
                )
                device.status = "idle"
                device.current_task_id = None
                device.last_heartbeat = datetime.now()
                released_count += 1
                continue

        if released_count > 0:
            self.db.commit()
            logger.info("Released %d timeout/broken devices", released_count)

        return released_count

    # ── 设备获取与锁定 ────────────────────────────────────────

    def acquire_device(self, task_id: int, user_id: Optional[int] = None) -> Optional[Device]:
        """从云手机池（available + 有效 ADB）获取一台 idle 设备并锁定；池内有机器但暂忙时会等待轮询。
        user_id 非空时仅使用 cloud_phone_pool.created_by == user_id 的实例，避免多用户串设备。
        
        增加超时检测：在尝试获取设备前，先检查是否有超时任务绑定的设备，如有则自动释放。
        """
        deadline = time.monotonic() + ACQUIRE_WAIT_SECONDS

        # 在获取设备前，先检查并释放超时任务绑定的设备（处理服务器重启导致的卡死）
        self._check_and_release_timeout_devices(user_id=user_id)

        while time.monotonic() < deadline:
            self._sync_cloud_phones_to_device_pool(user_id=user_id)
            cloud_serials = self._list_cloud_pool_adb_serials(user_id=user_id)
            if not cloud_serials:
                logger.warning(
                    "No available cloud phone with adb_host_port for task %s user_id=%s",
                    task_id,
                    user_id,
                )
                return None

            device = self._try_acquire_from_cloud_pool(task_id, user_id=user_id)
            if device:
                return device

            # 尝试恢复离线/错误设备
            recovered = self._recover_devices(cloud_serials)
            if recovered:
                device = self._try_acquire_from_cloud_pool(task_id, user_id=user_id)
                if device:
                    return device

            # 再次检查超时设备（处理等待期间超时的情况）
            self._check_and_release_timeout_devices(user_id=user_id)

            time.sleep(ACQUIRE_POLL_INTERVAL)

        logger.warning("Timeout waiting for cloud pool device (task_id=%s user_id=%s)", task_id, user_id)
        return None

    def _list_cloud_pool_adb_serials(self, user_id: Optional[int] = None) -> Set[str]:
        q = self.db.query(CloudPhonePool.adb_host_port).filter(
            CloudPhonePool.status == "available",
            CloudPhonePool.adb_host_port.isnot(None),
        )
        if user_id is not None:
            q = q.filter(CloudPhonePool.created_by == user_id)
        rows = q.all()
        out: set[str] = set()
        for (adb,) in rows:
            if adb and (s := adb.strip()):
                out.add(s)
        return out

    def _sync_cloud_phones_to_device_pool(self, user_id: Optional[int] = None) -> None:
        """为可用云手机自动补全 device_pool 行（adb_host_port 即 ADB serial）。"""
        try:
            q = self.db.query(CloudPhonePool).filter(
                CloudPhonePool.status == "available",
                CloudPhonePool.adb_host_port.isnot(None),
            )
            if user_id is not None:
                q = q.filter(CloudPhonePool.created_by == user_id)
            phones = q.all()
            for cp in phones:
                serial = (cp.adb_host_port or "").strip()
                if not serial:
                    continue
                if self.db.query(Device).filter(Device.device_id == serial).first():
                    continue
                name = (cp.phone_name or cp.phone_id or serial)[:128]
                self.db.add(
                    Device(
                        device_id=serial,
                        device_name=name,
                        device_type="cloud_phone",
                        status="idle",
                    )
                )
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            logger.debug("device_pool sync skipped (concurrent insert)")

    def _try_acquire_from_cloud_pool(self, task_id: int, user_id: Optional[int] = None) -> Optional[Device]:
        """在云手机池可用的实例中锁定一台 idle 设备（SKIP LOCKED 便于并行多任务）。"""
        q = (
            self.db.query(Device)
            .join(
                CloudPhonePool,
                func.trim(CloudPhonePool.adb_host_port) == Device.device_id,
            )
            .filter(
                Device.status == "idle",
                CloudPhonePool.status == "available",
                CloudPhonePool.adb_host_port.isnot(None),
                func.trim(CloudPhonePool.adb_host_port) != "",
            )
        )
        if user_id is not None:
            q = q.filter(CloudPhonePool.created_by == user_id)
        q = q.order_by(CloudPhonePool.id).with_for_update(skip_locked=True)
        device = q.first()

        if not device:
            return None

        adb = AdbClient(serial=device.device_id)
        adb.ensure_connected()
        if not adb.is_connected():
            device.status = "offline"
            device.last_heartbeat = datetime.now()
            self.db.commit()
            logger.warning("Device %s offline during acquire", device.device_id)
            return None

        device.status = "busy"
        device.current_task_id = task_id
        device.last_heartbeat = datetime.now()
        device.error_count = 0
        self.db.commit()
        logger.info("Acquired device %s for task %d (cloud pool)", device.device_id, task_id)
        return device

    def _recover_devices(self, only_device_ids: Optional[set[str]] = None) -> int:
        """尝试重连 offline/error 设备，恢复成功则置为 idle。only_device_ids 非空时只处理列表内 serial。"""
        query = self.db.query(Device).filter(Device.status.in_(RECOVERABLE_STATUSES))
        if only_device_ids is not None:
            if not only_device_ids:
                return 0
            query = query.filter(Device.device_id.in_(only_device_ids))
        candidates = query.all()

        if not candidates:
            return 0

        recovered = 0
        for device in candidates:
            logger.info("Attempting to recover %s device %s ...",
                        device.status, device.device_id)
            adb = AdbClient(serial=device.device_id)

            connected = False
            for attempt in range(1, ADB_RECONNECT_RETRIES + 1):
                adb._connected = False
                adb.ensure_connected()
                if adb.is_connected():
                    connected = True
                    break
                logger.info("Recovery attempt %d/%d for %s failed, retrying...",
                            attempt, ADB_RECONNECT_RETRIES, device.device_id)
                time.sleep(ADB_RECONNECT_INTERVAL)

            device.last_heartbeat = datetime.now()
            if connected:
                device.status = "idle"
                device.error_count = 0
                recovered += 1
                logger.info("Device %s recovered -> idle", device.device_id)
            else:
                logger.warning("Device %s still unreachable after %d retries",
                               device.device_id, ADB_RECONNECT_RETRIES)
            self.db.commit()

        return recovered

    def release_device(self, serial: str, success: bool = True):
        """释放设备锁。"""
        device = self.db.query(Device).filter(Device.device_id == serial).first()
        if not device:
            return
        if success:
            device.status = "idle"
            device.error_count = 0
        else:
            device.error_count += 1
            if device.error_count >= 5:
                device.status = "error"
                logger.error("Device %s marked as error (consecutive failures: %d)",
                             serial, device.error_count)
            else:
                device.status = "idle"
        device.current_task_id = None
        device.last_heartbeat = datetime.now()
        self.db.commit()

    # ── 设备预热 ──────────────────────────────────────────────

    def warm_up(self, serial: str) -> bool:
        """确保设备处于可用状态：屏幕亮、拼多多已装、回到桌面。"""
        adb = AdbClient(serial=serial)
        adb.ensure_connected()

        if not adb.is_connected():
            logger.error("Device %s not connected", serial)
            return False

        adb.ensure_screen_on()
        adb.disable_animations()
        adb.set_screen_timeout(1800000)

        if not adb.is_app_installed(PDD_PACKAGE):
            logger.error("PDD not installed on %s", serial)
            return False

        adb.press_home()
        time.sleep(0.5)

        logger.info("Device %s warmed up", serial)
        return True

    # ── 心跳检查 ──────────────────────────────────────────────

    def heartbeat(self, serial: str) -> bool:
        adb = AdbClient(serial=serial)
        adb.ensure_connected()
        connected = adb.is_connected()
        device = self.db.query(Device).filter(Device.device_id == serial).first()
        if device:
            device.last_heartbeat = datetime.now()
            if connected and device.status in RECOVERABLE_STATUSES:
                device.status = "idle"
                device.error_count = 0
                logger.info("Device %s recovered via heartbeat -> idle", serial)
            elif not connected and device.status not in ("busy",):
                device.status = "offline"
            self.db.commit()
        return connected

    def heartbeat_all(self):
        devices = self.db.query(Device).all()
        for d in devices:
            self.heartbeat(d.device_id)

    # ── 信息查询 ──────────────────────────────────────────────

    def get_device(self, serial: str) -> Optional[Device]:
        return self.db.query(Device).filter(Device.device_id == serial).first()

    def list_devices(self) -> list[Device]:
        return self.db.query(Device).all()

    def get_idle_count(self) -> int:
        """获取云手机池中处于空闲状态的设备数量。
        
        注意：只统计云手机池（cloud_phone_pool）中的设备，
        因为拍照购任务只能使用云手机池中的设备。
        """
        # 获取云手机池中的设备序列号
        cloud_serials = self._list_cloud_pool_adb_serials(user_id=None)
        if not cloud_serials:
            return 0
        # 只统计云手机池中状态为 idle 的设备
        return self.db.query(Device).filter(
            Device.device_id.in_(cloud_serials),
            Device.status == "idle"
        ).count()
