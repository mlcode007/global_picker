from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.profit_record import ProfitRecord
from app.models.exchange_rate import ExchangeRate
from app.schemas.profit import ProfitCalcRequest


def get_exchange_rate(db: Session, currency: str) -> Optional[Decimal]:
    """从数据库获取汇率"""
    rate = db.query(ExchangeRate).filter(ExchangeRate.currency == currency).first()
    return rate.rate_to_cny if rate else None


def calculate_profit(db: Session, req: ProfitCalcRequest) -> ProfitRecord:
    """计算利润并持久化"""
    platform_fee = (req.tiktok_price_cny * req.platform_fee_rate).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    total_cost = req.pdd_price_cny + req.logistics_cost + platform_fee + req.other_cost
    profit = (req.tiktok_price_cny - total_cost).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    profit_rate = (
        (profit / req.tiktok_price_cny).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        if req.tiktok_price_cny > 0
        else Decimal("0")
    )

    record = ProfitRecord(
        product_id=req.product_id,
        pdd_match_id=req.pdd_match_id,
        tiktok_price_cny=req.tiktok_price_cny,
        pdd_price_cny=req.pdd_price_cny,
        logistics_cost=req.logistics_cost,
        platform_fee_rate=req.platform_fee_rate,
        platform_fee=platform_fee,
        other_cost=req.other_cost,
        profit=profit,
        profit_rate=profit_rate,
        exchange_rate=req.exchange_rate,
        note=req.note,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_profit_history(db: Session, product_id: int) -> List[ProfitRecord]:
    return (
        db.query(ProfitRecord)
        .filter(ProfitRecord.product_id == product_id)
        .order_by(ProfitRecord.created_at.desc())
        .all()
    )
