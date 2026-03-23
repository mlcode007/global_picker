"""
拍照购任务服务 —— 任务创建、状态管理、结果入库。
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.photo_search_task import PhotoSearchTask, DeviceActionLog
from app.models.product import Product
from app.models.pdd_match import PddMatch
from app.models.device import Device

logger = logging.getLogger(__name__)

STALE_TASK_TIMEOUT_MINUTES = 10

_product_locks: dict[int, float] = {}
_lock_mutex = threading.Lock()
_LOCK_TTL_SECONDS = 30


class DuplicateTaskError(Exception):
    """商品已有进行中的拍照购任务"""
    def __init__(self, product_id: int, task_id: int):
        self.product_id = product_id
        self.task_id = task_id
        super().__init__(f"商品 {product_id} 已有进行中的拍照购任务 #{task_id}")


def _acquire_product_lock(product_id: int) -> bool:
    with _lock_mutex:
        now = time.monotonic()
        if product_id in _product_locks:
            if now - _product_locks[product_id] < _LOCK_TTL_SECONDS:
                return False
        _product_locks[product_id] = now
        return True


def _release_product_lock(product_id: int):
    with _lock_mutex:
        _product_locks.pop(product_id, None)


def _expire_stale_task(db: Session, task: PhotoSearchTask) -> bool:
    if not task.created_at:
        return False
    deadline = datetime.now() - timedelta(minutes=STALE_TASK_TIMEOUT_MINUTES)
    ref_time = task.started_at or task.created_at
    if ref_time < deadline:
        logger.warning(
            "Task #%d for product #%d stale (created %s), auto-failing",
            task.id, task.product_id, task.created_at,
        )
        task.status = "failed"
        task.error_code = "STALE_TIMEOUT"
        task.error_message = f"任务超过 {STALE_TASK_TIMEOUT_MINUTES} 分钟未完成，已自动标记失败"
        task.finished_at = datetime.now()
        db.commit()
        return True
    return False


RUNNING_STATUSES = ("queued", "dispatching", "running", "collecting", "parsing", "saving")


def recover_interrupted_tasks(db: Session) -> int:
    """服务启动时调用：将所有中间状态的任务标记为 queued 以便自动重试，释放卡住的设备。"""
    tasks = db.query(PhotoSearchTask).filter(
        PhotoSearchTask.status.in_(RUNNING_STATUSES)
    ).all()

    if not tasks:
        return 0

    recovered = 0
    for task in tasks:
        old_status = task.status
        task.status = "queued"
        task.step = None
        task.error_code = None
        task.error_message = None
        task.started_at = None
        task.finished_at = None
        task.elapsed_ms = None
        task.device_id = None
        recovered += 1
        logger.info("Recovered task #%d (was %s) -> queued", task.id, old_status)

    busy_devices = db.query(Device).filter(Device.status == "busy").all()
    for device in busy_devices:
        device.status = "idle"
        device.current_task_id = None
        logger.info("Released stuck device %s -> idle", device.device_id)

    db.commit()
    return recovered


def create_task(db: Session, product_id: int, image_index: int = 0) -> PhotoSearchTask:
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise ValueError(f"商品 {product_id} 不存在")

    images = []
    if product.main_image_url:
        images.append(product.main_image_url)
    if product.image_urls:
        images.extend([u for u in product.image_urls if u not in images])

    if not images:
        raise ValueError(f"商品 {product_id} 没有可用图片")

    if image_index >= len(images):
        image_index = 0

    if not _acquire_product_lock(product_id):
        running = db.query(PhotoSearchTask).filter(
            PhotoSearchTask.product_id == product_id,
            PhotoSearchTask.status.in_(["queued", "dispatching", "running", "collecting", "parsing", "saving"]),
        ).first()
        task_id = running.id if running else 0
        raise DuplicateTaskError(product_id, task_id)

    try:
        running = db.query(PhotoSearchTask).filter(
            PhotoSearchTask.product_id == product_id,
            PhotoSearchTask.status.in_(["queued", "dispatching", "running", "collecting", "parsing", "saving"]),
        ).first()
        if running:
            if _expire_stale_task(db, running):
                pass
            else:
                raise DuplicateTaskError(product_id, running.id)

        task = PhotoSearchTask(
            product_id=product_id,
            status="queued",
            source_image_url=images[image_index],
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        logger.info("Created photo search task #%d for product #%d", task.id, product_id)
        return task
    except Exception:
        _release_product_lock(product_id)
        raise


def get_task(db: Session, task_id: int) -> Optional[PhotoSearchTask]:
    return db.query(PhotoSearchTask).filter(PhotoSearchTask.id == task_id).first()


def get_tasks_by_product(db: Session, product_id: int) -> List[PhotoSearchTask]:
    return (
        db.query(PhotoSearchTask)
        .filter(PhotoSearchTask.product_id == product_id)
        .order_by(PhotoSearchTask.created_at.desc())
        .limit(20)
        .all()
    )


def update_task_status(
    db: Session,
    task_id: int,
    status: str,
    step: str = None,
    error_code: str = None,
    error_message: str = None,
    device_id: str = None,
    candidates_found: int = None,
    candidates_saved: int = None,
    raw_result_json: dict = None,
):
    task = db.query(PhotoSearchTask).filter(PhotoSearchTask.id == task_id).first()
    if not task:
        return

    task.status = status
    if step is not None:
        task.step = step
    if error_code is not None:
        task.error_code = error_code
    if error_message is not None:
        task.error_message = error_message
    if device_id is not None:
        task.device_id = device_id
    if candidates_found is not None:
        task.candidates_found = candidates_found
    if candidates_saved is not None:
        task.candidates_saved = candidates_saved
    if raw_result_json is not None:
        task.raw_result_json = raw_result_json

    if status == "running" and task.started_at is None:
        task.started_at = datetime.now()
    if status in ("success", "failed", "cancelled"):
        task.finished_at = datetime.now()
        if task.started_at:
            task.elapsed_ms = int((task.finished_at - task.started_at).total_seconds() * 1000)
        _release_product_lock(task.product_id)

    db.commit()


def retry_task(db: Session, task_id: int) -> PhotoSearchTask:
    task = db.query(PhotoSearchTask).filter(PhotoSearchTask.id == task_id).first()
    if not task:
        raise ValueError(f"任务 {task_id} 不存在")

    if task.status not in ("failed", "cancelled"):
        raise ValueError(f"任务 #{task_id} 状态为 {task.status}，不可重试")

    if task.attempt_count >= task.max_attempts:
        raise ValueError(f"任务 #{task_id} 已达最大重试次数 {task.max_attempts}")

    task.status = "queued"
    task.step = None
    task.error_code = None
    task.error_message = None
    task.started_at = None
    task.finished_at = None
    task.elapsed_ms = None
    db.commit()
    db.refresh(task)
    return task


def cancel_task(db: Session, task_id: int):
    task = db.query(PhotoSearchTask).filter(PhotoSearchTask.id == task_id).first()
    if not task:
        raise ValueError(f"任务 {task_id} 不存在")
    if task.status in ("success", "cancelled"):
        return task
    task.status = "cancelled"
    task.finished_at = datetime.now()
    _release_product_lock(task.product_id)
    db.commit()
    db.refresh(task)
    return task


def save_action_log(
    db: Session,
    task_id: int,
    device_id: str,
    step: str,
    action: str,
    success: bool = True,
    elapsed_ms: int = None,
    screenshot_path: str = None,
    xml_dump_path: str = None,
    ocr_text: str = None,
    message: str = None,
    extra: dict = None,
):
    log = DeviceActionLog(
        task_id=task_id,
        device_id=device_id,
        step=step,
        action=action,
        success=1 if success else 0,
        elapsed_ms=elapsed_ms,
        screenshot_path=screenshot_path,
        xml_dump_path=xml_dump_path,
        ocr_text=ocr_text,
        message=message,
        extra=extra,
    )
    db.add(log)
    db.commit()


def get_action_logs(db: Session, task_id: int) -> List[DeviceActionLog]:
    return (
        db.query(DeviceActionLog)
        .filter(DeviceActionLog.task_id == task_id)
        .order_by(DeviceActionLog.created_at)
        .all()
    )


def save_candidates_to_matches(
    db: Session,
    product_id: int,
    candidates: list,
) -> int:
    """把解析出的候选写入 pdd_matches，去重后返回新增条数。"""
    saved = 0
    for item in candidates:
        if not item.is_valid:
            continue

        existing = db.query(PddMatch).filter(
            PddMatch.product_id == product_id,
            PddMatch.pdd_title == item.title,
            PddMatch.pdd_price == item.price,
        ).first()
        if existing:
            # 若已存在但缺少图片，补充更新
            if not existing.pdd_image_url and item.image_url:
                existing.pdd_image_url = item.image_url
                db.commit()
            continue

        match = PddMatch(
            product_id=product_id,
            pdd_title=item.title,
            pdd_price=item.price,
            pdd_original_price=item.original_price,
            pdd_sales_volume=item.sales_volume,
            pdd_shop_name=item.shop_name or None,
            pdd_image_url=item.image_url or None,
            match_source="image_search",
            match_confidence=None,
            is_confirmed=0,
            is_primary=0,
        )
        db.add(match)
        saved += 1

    if saved:
        db.commit()
    logger.info("Saved %d new matches for product #%d", saved, product_id)
    return saved
