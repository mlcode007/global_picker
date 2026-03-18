from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class PddMatchCreate(BaseModel):
    product_id: int
    pdd_title: str
    pdd_price: Decimal
    pdd_original_price: Optional[Decimal] = None
    pdd_sales_volume: Optional[int] = None
    pdd_shop_name: Optional[str] = None
    pdd_image_url: Optional[str] = None
    pdd_product_url: Optional[str] = None
    match_source: str = "manual"
    match_confidence: Optional[Decimal] = None
    is_confirmed: int = 0
    is_primary: int = 0


class PddMatchUpdate(BaseModel):
    is_confirmed: Optional[int] = None
    is_primary: Optional[int] = None
    pdd_price: Optional[Decimal] = None


class PddMatchOut(BaseModel):
    id: int
    product_id: int
    pdd_product_id: Optional[str]
    pdd_title: str
    pdd_price: Decimal
    pdd_original_price: Optional[Decimal]
    pdd_sales_volume: Optional[int]
    pdd_shop_name: Optional[str]
    pdd_image_url: Optional[str]
    pdd_product_url: Optional[str]
    match_source: str
    match_confidence: Optional[Decimal]
    is_confirmed: int
    is_primary: int
    created_at: datetime

    model_config = {"from_attributes": True}
