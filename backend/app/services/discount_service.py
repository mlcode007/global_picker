"""折扣码校验与履约辅助。"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models.discount_code import DiscountCode


class DiscountCodeError(Exception):
    """折扣码校验失败。"""
    pass


def _now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def validate_discount_code(db: Session, code: str, tier: str) -> DiscountCode:
    """校验折扣码是否可用于指定会员等级，返回折扣码对象。

    折扣码为一次性：使用后状态变为 used，不可再次使用。
    校验项：存在、启用、未使用、未过期、等级匹配。
    """
    code = (code or "").strip()
    if not code:
        raise DiscountCodeError("请输入折扣码")

    discount = db.query(DiscountCode).filter(DiscountCode.code == code).first()
    if not discount:
        raise DiscountCodeError("折扣码不存在")

    if not discount.is_active:
        raise DiscountCodeError("折扣码已停用")

    if discount.status == "used":
        raise DiscountCodeError("折扣码已被使用，不可重复使用")

    if discount.tier != tier:
        tier_name = {"basic": "基础版", "pro": "专业版"}.get(discount.tier, discount.tier)
        raise DiscountCodeError(f"该折扣码仅适用于{tier_name}")

    if discount.expires_at is not None and discount.expires_at < _now_naive():
        raise DiscountCodeError("折扣码已过期")

    return discount


def consume_discount_code(db: Session, code: str) -> None:
    """履约成功后将折扣码标记为已使用（一次性，不提交事务）。"""
    code = (code or "").strip()
    if not code:
        return
    discount = db.query(DiscountCode).filter(DiscountCode.code == code).first()
    if discount and discount.status != "used":
        discount.status = "used"
        discount.used_count = (discount.used_count or 0) + 1
