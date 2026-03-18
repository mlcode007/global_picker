"""
设备池管理器 —— 设备获取、加锁、释放、心跳、异常标记。

即使当前只有一台 MNYHYHBQOZDQS89H，也按池化抽象设计，
后续扩多设备零改动。
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.device import Device
from .adb_client import AdbClient

logger = logging.getLogger(__name__)

PDD_PACKAGE = "com.xunmeng.pinduoduo"


class DeviceManager:

    def __init__(self, db: Session):
        self.db = db

    # ── 设备获取与锁定 ────────────────────────────────────────

    def acquire_device(self, task_id: int, preferred_serial: str | None = None) -> Optional[Device]:
        """从池中获取一台空闲设备并锁定。"""
        query = self.db.query(Device).filter(Device.status == "idle")
        if preferred_serial:
            query = query.filter(Device.device_id == preferred_serial)
        device = query.with_for_update(skip_locked=True).first()

        if not device:
            logger.warning("No idle device available (preferred=%s)", preferred_serial)
            return None

        adb = AdbClient(serial=device.device_id)
        adb.ensure_connected()
        if not adb.is_connected():
            device.status = "offline"
            device.last_heartbeat = datetime.now()
            self.db.commit()
            logger.warning("Device %s offline", device.device_id)
            return None

        device.status = "busy"
        device.current_task_id = task_id
        device.last_heartbeat = datetime.now()
        device.error_count = 0
        self.db.commit()
        logger.info("Acquired device %s for task %d", device.device_id, task_id)
        return device

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
        import time
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
            if not connected and device.status != "busy":
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
