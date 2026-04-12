"""
设备池管理器 —— 设备获取、加锁、释放、心跳、异常标记。

拍照购调度：只使用「云手机池」中状态为 available 且已配置 adb_host_port 的实例；
与 device_pool 行级锁（FOR UPDATE SKIP LOCKED）配合，多任务可并行占用不同设备。
"""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.cloud_phone import CloudPhonePool
from app.models.device import Device
from .adb_client import AdbClient

logger = logging.getLogger(__name__)

PDD_PACKAGE = "com.xunmeng.pinduoduo"

RECOVERABLE_STATUSES = ("offline", "error")
ADB_RECONNECT_RETRIES = 2
ADB_RECONNECT_INTERVAL = 2

# 多任务抢少量设备时：在超时内轮询，避免瞬时无 idle 就立刻 NO_DEVICE
ACQUIRE_WAIT_SECONDS = 600
ACQUIRE_POLL_INTERVAL = 2.0


class DeviceManager:

    def __init__(self, db: Session):
        self.db = db

    # ── 设备获取与锁定 ────────────────────────────────────────

    def acquire_device(self, task_id: int) -> Optional[Device]:
        """从云手机池（available + 有效 ADB）获取一台 idle 设备并锁定；池内有机器但暂忙时会等待轮询。"""
        deadline = time.monotonic() + ACQUIRE_WAIT_SECONDS

        while time.monotonic() < deadline:
            self._sync_cloud_phones_to_device_pool()
            cloud_serials = self._list_cloud_pool_adb_serials()
            if not cloud_serials:
                logger.warning(
                    "No available cloud phone with adb_host_port for task %s",
                    task_id,
                )
                return None

            device = self._try_acquire_from_cloud_pool(task_id)
            if device:
                return device

            recovered = self._recover_devices(cloud_serials)
            if recovered:
                device = self._try_acquire_from_cloud_pool(task_id)
                if device:
                    return device

            time.sleep(ACQUIRE_POLL_INTERVAL)

        logger.warning("Timeout waiting for cloud pool device (task_id=%s)", task_id)
        return None

    def _list_cloud_pool_adb_serials(self) -> set[str]:
        rows = (
            self.db.query(CloudPhonePool.adb_host_port)
            .filter(
                CloudPhonePool.status == "available",
                CloudPhonePool.adb_host_port.isnot(None),
            )
            .all()
        )
        out: set[str] = set()
        for (adb,) in rows:
            if adb and (s := adb.strip()):
                out.add(s)
        return out

    def _sync_cloud_phones_to_device_pool(self) -> None:
        """为可用云手机自动补全 device_pool 行（adb_host_port 即 ADB serial）。"""
        try:
            phones = (
                self.db.query(CloudPhonePool)
                .filter(
                    CloudPhonePool.status == "available",
                    CloudPhonePool.adb_host_port.isnot(None),
                )
                .all()
            )
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

    def _try_acquire_from_cloud_pool(self, task_id: int) -> Optional[Device]:
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
            .order_by(CloudPhonePool.id)
            .with_for_update(skip_locked=True)
        )
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
        return self.db.query(Device).filter(Device.status == "idle").count()
