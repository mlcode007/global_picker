from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class ProfitCalcRequest(BaseModel):
    """利润计算请求"""
    product_id: int
    pdd_match_id: Optional[int] = None
    tiktok_price_cny: Decimal
    pdd_price_cny: Decimal
    logistics_cost: Decimal = Decimal("15.00")
    platform_fee_rate: Decimal = Decimal("0.05")
    other_cost: Decimal = Decimal("0.00")
    exchange_rate: Optional[Decimal] = None
    note: Optional[str] = None


class ProfitOut(BaseModel):
    id: int
    product_id: int
    pdd_match_id: Optional[int]
    tiktok_price_cny: Decimal
    pdd_price_cny: Decimal
    logistics_cost: Decimal
    platform_fee_rate: Decimal
    platform_fee: Decimal
    other_cost: Decimal
    profit: Decimal
    profit_rate: Decimal
    exchange_rate: Optional[Decimal]
    note: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
