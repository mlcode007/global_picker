"""
激活码 API
- 管理员：生成、查看、管理激活码
- 所有用户：兑换激活码
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user, require_admin
from app.models.user import User
from app.models.activation_code import ActivationCode, generate_activation_code
from app.schemas.common import Response

router = APIRouter(prefix="/activation", tags=["激活码"])


# ── Schemas ──

class ActivationCodeCreate(BaseModel):
    tier: str = Field(default="basic", description="会员等级: basic/pro")
    duration_months: int = Field(default=1, ge=1, le=36, description="有效期（月）")
    count: int = Field(default=1, ge=1, le=100, description="批量生成数量")
    remark: Optional[str] = Field(default=None, description="备注")
    expires_days: Optional[int] = Field(default=None, ge=1, description="激活码有效期（天），不填则永不过期")


class ActivationCodeRedeem(BaseModel):
    code: str = Field(..., description="激活码")


class ActivationCodeOut(BaseModel):
    id: int
    code: str
    tier: str
    duration_months: int
    max_uses: int
    used_count: int
    is_active: bool
    remark: Optional[str]
    expires_at: Optional[str]
    created_at: str


# ── Admin: 生成激活码 ──

@router.post("/generate", summary="生成激活码（管理员）")
def generate_codes(
    data: ActivationCodeCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """批量生成激活码，返回所有生成的码"""
    codes = []
    for _ in range(data.count):
        code_str = generate_activation_code()
        expires_at = None
        if data.expires_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=data.expires_days)

        ac = ActivationCode(
            code=code_str,
            tier=data.tier,
            duration_months=data.duration_months,
            max_uses=1,
            remark=data.remark,
            created_by=current_user.id,
            expires_at=expires_at,
        )
        db.add(ac)
        codes.append(code_str)

    db.commit()

    return Response(
        data={
            "codes": codes,
            "tier": data.tier,
            "duration_months": data.duration_months,
            "count": len(codes),
        },
        message=f"成功生成 {len(codes)} 个激活码",
    )


# ── Admin: 查询激活码列表 ──

@router.get("/codes", summary="激活码列表（管理员）")
def list_codes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    total = db.query(ActivationCode).count()
    codes = (
        db.query(ActivationCode)
        .order_by(ActivationCode.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return Response(data={
        "items": [ActivationCodeOut.model_validate(c).model_dump() for c in codes],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


# ── Admin: 禁用激活码 ──

@router.put("/codes/{code_id}/toggle", summary="启用/禁用激活码（管理员）")
def toggle_code(
    code_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ac = db.query(ActivationCode).filter(ActivationCode.id == code_id).first()
    if not ac:
        raise HTTPException(status_code=404, detail="激活码不存在")
    ac.is_active = not ac.is_active
    db.commit()
    status = "已禁用" if not ac.is_active else "已启用"
    return Response(message=f"激活码 {status}")


# ─ 所有用户: 兑换激活码 ──

@router.post("/redeem", summary="兑换激活码")
def redeem_code(
    data: ActivationCodeRedeem,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """用户兑换激活码，自动开通对应会员"""
    code_str = data.code.strip().upper()

    ac = db.query(ActivationCode).filter(ActivationCode.code == code_str).first()
    if not ac:
        raise HTTPException(status_code=404, detail="激活码无效")

    # 检查激活码状态
    if not ac.is_active:
        raise HTTPException(status_code=400, detail="该激活码已禁用")

    if ac.used_count >= ac.max_uses:
        raise HTTPException(status_code=400, detail="该激活码已达使用上限")

    if ac.expires_at and datetime.now(timezone.utc) > ac.expires_at.replace(tzinfo=timezone.utc):
        raise HTTPException(status_code=400, detail="该激活码已过期")

    # 计算会员到期时间
    now = datetime.now(timezone.utc)
    if current_user.membership_tier == ac.tier and current_user.membership_expires_at:
        # 同等级续费，在现有到期时间基础上延长
        base = current_user.membership_expires_at.replace(tzinfo=timezone.utc)
        if base < now:
            base = now
    else:
        base = now

    new_expires = base + timedelta(days=ac.duration_months * 30)

    # 更新用户会员等级
    current_user.membership_tier = ac.tier
    current_user.membership_expires_at = new_expires.replace(tzinfo=None)

    # 更新激活码使用次数
    ac.used_count += 1

    db.commit()

    tier_names = {"basic": "基础版", "pro": "专业版"}
    tier_name = tier_names.get(ac.tier, ac.tier)

    return Response(
        data={
            "tier": ac.tier,
            "tier_name": tier_name,
            "expires_at": new_expires.isoformat(),
        },
        message=f"兑换成功！已开通 {tier_name}，有效期至 {new_expires.strftime('%Y-%m-%d')}",
    )


# ── 所有用户: 查询我的激活记录 ──

@router.get("/my-codes", summary="我的兑换记录")
def my_codes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询当前用户通过激活码开通的记录（通过 remark 关联不太现实，简化为返回当前会员状态）"""
    return Response(data={
        "tier": current_user.membership_tier,
        "expires_at": current_user.membership_expires_at.isoformat() if current_user.membership_expires_at else None,
    })
