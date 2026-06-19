"""
会员系统 API
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.common import Response
from app.core.membership import TIER_LIMITS, MEMBERSHIP_PRICES, CLOUD_PHONE_PRICE, CLOUD_PHONE_MAX
from app.services.quota_service import QuotaManager

router = APIRouter(prefix="/membership", tags=["会员"])


@router.get("/status", summary="获取当前会员状态")
def get_membership_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的会员状态、配额使用情况、云手机订阅"""
    tier = current_user.membership_tier or "free"
    expires_at = current_user.membership_expires_at

    # 检查是否过期
    is_expired = False
    if tier != "free" and expires_at:
        if datetime.now(timezone.utc) > expires_at.replace(tzinfo=timezone.utc):
            is_expired = True
            tier = "free"

    # 配额状态
    quota_manager = QuotaManager(db)
    quota_status = quota_manager.get_quota_status(current_user.id)

    # 云手机订阅数（有效订阅，含空位与未到期已开通）
    from app.services.cloud_phone_service import CloudPhoneManager
    quota = CloudPhoneManager(db).get_subscription_quota(current_user.id)
    active_subs = quota["subscription_count"]

    return Response(data={
        "tier": tier,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "is_expired": is_expired,
        "daily_collect_limit": TIER_LIMITS[tier]["daily_collect"],
        "quota": quota_status,
        "cloud_phone_subscriptions": active_subs,
        "cloud_phone_max": CLOUD_PHONE_MAX,
        "cloud_phone_provisioned": quota["provisioned_count"],
        "cloud_phone_available_slots": quota["available_slots"],
        "cloud_phone_over_limit": quota["over_limit"],
    })


@router.get("/plans", summary="获取会员套餐信息")
def get_membership_plans():
    """获取所有会员套餐信息（公开接口）"""
    plans = []
    for tier, limits in TIER_LIMITS.items():
        plan = {
            "tier": tier,
            "daily_collect": limits["daily_collect"] if limits["daily_collect"] < 999999 else "不限",
            "price": MEMBERSHIP_PRICES.get(tier, 0),
            "price_label": f"¥{MEMBERSHIP_PRICES.get(tier, 0)}/月" if tier != "free" else "免费",
        }
        plans.append(plan)

    return Response(data={
        "plans": plans,
        "cloud_phone": {
            "price": CLOUD_PHONE_PRICE,
            "price_label": f"¥{CLOUD_PHONE_PRICE}/月/台",
            "max": CLOUD_PHONE_MAX,
        },
    })
