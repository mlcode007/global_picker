"""折扣码管理与校验 API。

- 管理员：折扣码的增删改查（生成模块，仅 admin 可见）。
- 普通用户：校验折扣码并返回调整后的会员价格。
"""
import random
import string
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user, require_admin
from app.models.user import User
from app.models.discount_code import DiscountCode
from app.schemas.common import Response
from app.core.membership import MEMBERSHIP_PRICES
from app.services.discount_service import validate_discount_code, DiscountCodeError

router = APIRouter(prefix="/discount", tags=["折扣码"])


def _to_naive(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _generate_code(db: Session, length: int = 10) -> str:
    alphabet = string.ascii_uppercase + string.digits
    for _ in range(20):
        code = "".join(random.choices(alphabet, k=length))
        if not db.query(DiscountCode).filter(DiscountCode.code == code).first():
            return code
    raise HTTPException(status_code=500, detail="生成折扣码失败，请重试")


def _serialize(d: DiscountCode) -> dict:
    return {
        "id": d.id,
        "code": d.code,
        "tier": d.tier,
        "price": float(d.price) if d.price is not None else None,
        "duration_months": d.duration_months or 1,
        "is_active": bool(d.is_active),
        "status": d.status,
        "max_uses": d.max_uses,
        "used_count": d.used_count or 0,
        "expires_at": d.expires_at.isoformat() if d.expires_at else None,
        "remark": d.remark,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


# ── 用户：校验折扣码 ──────────────────────────────────────────

class ValidateDiscountRequest(BaseModel):
    code: str
    tier: str

    @field_validator("tier")
    @classmethod
    def validate_tier(cls, v: str) -> str:
        if v not in ("basic", "pro"):
            raise ValueError("无效的会员等级")
        return v


@router.post("/validate", summary="校验折扣码并返回调整后价格")
def validate_code(
    request: ValidateDiscountRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        discount = validate_discount_code(db, request.code, request.tier)
    except DiscountCodeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Response(data={
        "code": discount.code,
        "tier": discount.tier,
        "price": float(discount.price),
        "original_price": float(MEMBERSHIP_PRICES[request.tier]),
        "duration_months": discount.duration_months or 1,
    })


# ── 管理员：折扣码 CRUD ───────────────────────────────────────

class CreateDiscountRequest(BaseModel):
    tier: str
    price: float
    duration_months: int = 1
    code: Optional[str] = None
    max_uses: Optional[int] = None
    expires_at: Optional[datetime] = None
    remark: Optional[str] = None
    is_active: bool = True

    @field_validator("tier")
    @classmethod
    def validate_tier(cls, v: str) -> str:
        if v not in ("basic", "pro"):
            raise ValueError("无效的会员等级，仅支持 basic 或 pro")
        return v

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        if v < 0:
            raise ValueError("价格不能为负")
        return v

    @field_validator("duration_months")
    @classmethod
    def validate_duration(cls, v: int) -> int:
        if v < 1 or v > 36:
            raise ValueError("会员有效期月数需在 1-36 之间")
        return v


class UpdateDiscountRequest(BaseModel):
    price: Optional[float] = None
    duration_months: Optional[int] = None
    max_uses: Optional[int] = None
    expires_at: Optional[datetime] = None
    remark: Optional[str] = None
    is_active: Optional[bool] = None
    status: Optional[str] = None

    @field_validator("price")
    @classmethod
    def validate_price(cls, v):
        if v is not None and v < 0:
            raise ValueError("价格不能为负")
        return v

    @field_validator("duration_months")
    @classmethod
    def validate_duration(cls, v):
        if v is not None and (v < 1 or v > 36):
            raise ValueError("会员有效期月数需在 1-36 之间")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v is not None and v not in ("unused", "used"):
            raise ValueError("无效的状态")
        return v


@router.get("/admin/codes", summary="折扣码列表（管理员）")
def list_codes(
    tier: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    query = db.query(DiscountCode)
    if tier in ("basic", "pro"):
        query = query.filter(DiscountCode.tier == tier)
    codes = query.order_by(DiscountCode.created_at.desc()).all()
    return Response(data={"items": [_serialize(c) for c in codes]})


@router.post("/admin/codes", summary="创建折扣码（管理员）")
def create_code(
    request: CreateDiscountRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    code = (request.code or "").strip().upper()
    if code:
        if db.query(DiscountCode).filter(DiscountCode.code == code).first():
            raise HTTPException(status_code=400, detail="折扣码已存在")
    else:
        code = _generate_code(db)

    discount = DiscountCode(
        code=code,
        tier=request.tier,
        price=Decimal(str(request.price)),
        duration_months=request.duration_months,
        is_active=1 if request.is_active else 0,
        max_uses=request.max_uses,
        used_count=0,
        expires_at=_to_naive(request.expires_at),
        remark=request.remark,
        created_by=admin.id,
    )
    db.add(discount)
    db.commit()
    db.refresh(discount)
    return Response(data=_serialize(discount))


@router.put("/admin/codes/{code_id}", summary="更新折扣码（管理员）")
def update_code(
    code_id: int,
    request: UpdateDiscountRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    discount = db.query(DiscountCode).filter(DiscountCode.id == code_id).first()
    if not discount:
        raise HTTPException(status_code=404, detail="折扣码不存在")

    if request.price is not None:
        discount.price = Decimal(str(request.price))
    if request.duration_months is not None:
        discount.duration_months = request.duration_months
    if request.max_uses is not None:
        discount.max_uses = request.max_uses
    if request.expires_at is not None:
        discount.expires_at = _to_naive(request.expires_at)
    if request.remark is not None:
        discount.remark = request.remark
    if request.is_active is not None:
        discount.is_active = 1 if request.is_active else 0
    if request.status is not None:
        discount.status = request.status
        if request.status == "unused":
            discount.used_count = 0

    db.commit()
    db.refresh(discount)
    return Response(data=_serialize(discount))


@router.delete("/admin/codes/{code_id}", summary="删除折扣码（管理员）")
def delete_code(
    code_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    discount = db.query(DiscountCode).filter(DiscountCode.id == code_id).first()
    if not discount:
        raise HTTPException(status_code=404, detail="折扣码不存在")
    db.delete(discount)
    db.commit()
    return Response(data={"id": code_id})
