"""云手机到期处理：懒过期 + 定时销毁实例。"""
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.cloud_phone import CloudPhonePool, UserCloudPhone
from app.models.cloud_phone_subscription import CloudPhoneSubscription
from app.util.chinac.chinac_open_api import ChinacOpenApi

logger = logging.getLogger(__name__)

EXPIRY_INTERVAL_SEC = 3600


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _expire_one(db: Session, sub: CloudPhoneSubscription, api: ChinacOpenApi) -> bool:
    """销毁单台到期云手机并更新本地状态。"""
    pool = db.query(CloudPhonePool).filter(CloudPhonePool.id == sub.device_id).first()
    if not pool:
        sub.status = "expired"
        db.commit()
        logger.warning("订阅 %s 无对应 pool 记录，已标记 expired", sub.id)
        return True

    phone_id = pool.phone_id
    now = _utc_now_naive()

    try:
        api.do_delete_cloud_phone(phone_id)
    except Exception as e:
        logger.error("销毁云手机 %s 失败（订阅 %s）: %s", phone_id, sub.id, e)
        db.rollback()
        return False

    pool.status = "deleted"
    pool.updated_at = now
    sub.status = "expired"

    bindings = db.query(UserCloudPhone).filter(
        UserCloudPhone.phone_id == phone_id,
        UserCloudPhone.is_active == True,
    ).all()
    for binding in bindings:
        binding.is_active = False
        binding.unbind_at = now
        binding.updated_at = now

    db.commit()
    logger.info("云手机 %s 已到期销毁，订阅 %s 标记 expired", phone_id, sub.id)
    return True


def expire_due_subscriptions(db: Session, user_id: Optional[int] = None) -> int:
    """处理已到期的活跃订阅，返回成功处理数量。"""
    now = _utc_now_naive()
    query = db.query(CloudPhoneSubscription).filter(
        CloudPhoneSubscription.status == "active",
        CloudPhoneSubscription.device_id.isnot(None),
        CloudPhoneSubscription.expires_at.isnot(None),
        CloudPhoneSubscription.expires_at < now,
    )
    if user_id is not None:
        query = query.filter(CloudPhoneSubscription.user_id == user_id)

    due_subs = query.all()
    if not due_subs:
        return 0

    api = ChinacOpenApi()
    processed = 0
    for sub in due_subs:
        if _expire_one(db, sub, api):
            processed += 1
    return processed


def run_expiry_scan():
    """定时扫描全部到期订阅。"""
    db = SessionLocal()
    try:
        count = expire_due_subscriptions(db)
        if count:
            logger.info("到期扫描完成，处理 %d 条订阅", count)
    except Exception as e:
        logger.error("到期扫描异常: %s", e)
        db.rollback()
    finally:
        db.close()


def start_expiry_scheduler():
    """启动后台到期定时任务。"""

    def run_scheduler():
        while True:
            try:
                run_expiry_scan()
            except Exception as e:
                logger.error("到期定时任务异常: %s", e)
            time.sleep(EXPIRY_INTERVAL_SEC)

    thread = threading.Thread(target=run_scheduler, daemon=True)
    thread.start()
    logger.info("云手机到期定时任务已启动，间隔 %d 秒", EXPIRY_INTERVAL_SEC)
