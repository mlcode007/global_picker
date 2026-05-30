from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel


class Alibaba1688ProductItem(BaseModel):
    """插件采集的单个1688商品数据"""
    offerId: str = ""
    memberId: str = ""
    title: str = ""
    images: List[str] = []
    mainImage: str = ""
    price: float = 0
    consignPrice: float = 0
    last30DaysSales: str = ""
    totalSales: str = ""
    goodRates: float = 0
    repurchaseRate: str = ""
    tpYear: int = 0
    freeReturnIn7d: str = ""
    supportWaybill: str = ""


class Alibaba1688BatchCreate(BaseModel):
    """插件批量入库请求"""
    tiktok_product_id: Optional[str] = None
    product_id: int
    products: List[Alibaba1688ProductItem]
    sync_limit: Optional[int] = None


class Alibaba1688MatchCreate(BaseModel):
    product_id: int
    title: str
    price: Decimal
    offer_id: Optional[str] = None
    member_id: Optional[str] = None
    main_image: Optional[str] = None
    images: Optional[str] = None
    last30_days_sales: Optional[str] = None
    total_sales: Optional[str] = None
    good_rates: Optional[Decimal] = None
    repurchase_rate: Optional[str] = None
    tp_year: Optional[int] = None
    free_return_in7d: Optional[str] = None
    support_waybill: Optional[str] = None
    match_source: str = "image_search"
    is_confirmed: int = 0
    is_primary: int = 0


class Alibaba1688MatchUpdate(BaseModel):
    is_confirmed: Optional[int] = None
    is_primary: Optional[int] = None
    price: Optional[Decimal] = None


class Alibaba1688MatchOut(BaseModel):
    id: int
    product_id: int
    offer_id: Optional[str]
    member_id: Optional[str]
    title: str
    main_image: Optional[str]
    images: Optional[str]
    last30_days_sales: Optional[str]
    total_sales: Optional[str]
    good_rates: Optional[Decimal]
    repurchase_rate: Optional[str]
    tp_year: Optional[int]
    free_return_in7d: Optional[str]
    support_waybill: Optional[str]
    price: Decimal
    match_source: str
    is_confirmed: int
    is_primary: int
    created_at: datetime

    model_config = {"from_attributes": True}
