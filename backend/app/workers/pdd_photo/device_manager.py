"""
设备池管理器 —— 设备获取、加锁、释放、心跳、异常标记。

即使当前只有一台设备，也按池化抽象设计，后续扩多设备零改动。
"""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.device import Device
from .adb_client import AdbClient

logger = logging.getLogger(__name__)

PDD_PACKAGE = "com.xunmeng.pinduoduo"

RECOVERABLE_STATUSES = ("offline", "error")
ADB_RECONNECT_RETRIES = 2
ADB_RECONNECT_INTERVAL = 2


class DeviceManager:

    def __init__(self, db: Session):
        self.db = db

    # ── 设备获取与锁定 ────────────────────────────────────────

    def acquire_device(self, task_id: int, preferred_serial: str | None = None) -> Optional[Device]:
        """从池中获取一台空闲设备并锁定；若无空闲设备则尝试恢复离线/异常设备。"""
        device = self._try_acquire_idle(task_id, preferred_serial)
        if device:
            return device

        recovered = self._recover_devices(preferred_serial)
        if recovered:
            device = self._try_acquire_idle(task_id, preferred_serial)
            if device:
                return device

        logger.warning("No available device after recovery attempt (preferred=%s)", preferred_serial)
        return None

    def _try_acquire_idle(self, task_id: int, preferred_serial: str | None) -> Optional[Device]:
        """尝试获取一台 idle 设备，连接检测通过后锁定。"""
        query = self.db.query(Device).filter(Device.status == "idle")
        if preferred_serial:
            query = query.filter(Device.device_id == preferred_serial)
        device = query.with_for_update(skip_locked=True).first()

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
        logger.info("Acquired device %s for task %d", device.device_id, task_id)
        return device

    def _recover_devices(self, preferred_serial: str | None = None) -> int:
        """尝试重连 offline/error 设备，恢复成功则置为 idle。返回恢复数量。"""
        query = self.db.query(Device).filter(Device.status.in_(RECOVERABLE_STATUSES))
        if preferred_serial:
            query = query.filter(Device.device_id == preferred_serial)
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
