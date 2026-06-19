import logging
from datetime import datetime, timezone, timedelta, date
from sqlalchemy.orm import Session
from app.models.quota import UserQuota, CollectionHistory
from app.models.user import User
from app.core.membership import TIER_LIMITS, QUOTA_TIMEZONE

logger = logging.getLogger(__name__)

# 北京时间 UTC+8
_BJ_TZ = timezone(timedelta(hours=8))


class QuotaManager:
    """配额管理器 - 负责用户每日采集配额的管理"""

    def __init__(self, db: Session):
        self.db = db

    def _get_today(self) -> date:
        """按北京时间获取当天日期"""
        return datetime.now(_BJ_TZ).date()

    def _get_user_tier(self, user_id: int) -> str:
        """获取用户有效会员等级（检查是否过期）"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return "free"
        tier = user.membership_tier or "free"
        # 检查会员是否过期
        if tier != "free" and user.membership_expires_at:
            if datetime.now(timezone.utc) > user.membership_expires_at.replace(tzinfo=timezone.utc):
                tier = "free"
        return tier

    def _get_or_create_quota(self, user_id: int) -> UserQuota:
        today = self._get_today()
        tier = self._get_user_tier(user_id)
        daily_limit = TIER_LIMITS[tier]["daily_collect"]

        quota = self.db.query(UserQuota).filter(
            UserQuota.user_id == user_id,
            UserQuota.quota_date == today,
        ).first()

        if not quota:
            quota = UserQuota(
                user_id=user_id,
                quota_date=today,
                daily_limit=daily_limit,
            )
            self.db.add(quota)
            self.db.commit()
            self.db.refresh(quota)
        else:
            # 如果会员等级变化导致限额不同，更新限额
            if quota.daily_limit != daily_limit:
                quota.daily_limit = daily_limit
                self.db.commit()

        return quota

    def get_quota_status(self, user_id: int) -> dict:
        """获取用户今日配额状态"""
        quota = self._get_or_create_quota(user_id)
        remaining = quota.daily_limit - quota.used_count
        tier = self._get_user_tier(user_id)
        return {
            "today_count": quota.used_count,
            "daily_limit": quota.daily_limit,
            "remaining": max(0, remaining),
            "tier": tier,
        }

    def check_quota(self, user_id: int) -> bool:
        """检查用户今日配额是否充足"""
        status = self.get_quota_status(user_id)
        return status["remaining"] > 0

    def record_collection(self, user_id: int, product_url: str = None, product_id: int = None) -> dict:
        """记录一次采集操作"""
        quota = self._get_or_create_quota(user_id)

        if quota.used_count >= quota.daily_limit:
            logger.warning("User %d quota exceeded for today", user_id)
            return {
                "success": False,
                "error": {
                    "code": "QUOTA_EXCEEDED",
                    "message": f"今日采集配额已用完（{quota.used_count}/{quota.daily_limit}）",
                },
            }

        quota.used_count += 1

        history = CollectionHistory(
            user_id=user_id,
            product_url=product_url,
            product_id=product_id,
        )
        self.db.add(history)
        self.db.commit()

        remaining = quota.daily_limit - quota.used_count
        logger.info("User %d collected, used: %d/%d, remaining: %d",
                    user_id, quota.used_count, quota.daily_limit, remaining)

        return {
            "success": True,
            "data": {
                "today_count": quota.used_count,
                "daily_limit": quota.daily_limit,
                "remaining": remaining,
            },
        }
