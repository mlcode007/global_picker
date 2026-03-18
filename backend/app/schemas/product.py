from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel


class ProductCreate(BaseModel):
    """新增商品（手动录入或批量导入）"""
    tiktok_url: str
    title: Optional[str] = ""
    price: Optional[Decimal] = None
    currency: str = "PHP"
    sales_volume: Optional[int] = 0
    region: str = "PH"
    remark: Optional[str] = None


class ProductBatchImport(BaseModel):
    """批量导入，只需 URL 列表"""
    urls: List[str]


class ProductUpdate(BaseModel):
    """更新商品状态/备注"""
    status: Optional[str] = None
    remark: Optional[str] = None
    title: Optional[str] = None
    price_cny: Optional[Decimal] = None


class ProductOut(BaseModel):
    """商品列表/详情响应"""
    id: int
    tiktok_url: str
    tiktok_product_id: Optional[str]
    crawl_task_id: Optional[int] = None
    title: str
    price: Optional[Decimal]
    original_price: Optional[Decimal] = None
    discount: Optional[str] = None
    currency: str
    price_cny: Optional[Decimal]
    sales_volume: int
    rating: Optional[Decimal]
    review_count: int
    stock_status: int
    region: str
    shop_name: Optional[str]
    shop_id: Optional[str] = None
    seller_location: Optional[str] = None
    shipping_fee: Optional[Decimal] = None
    free_shipping: Optional[int] = 0
    delivery_days_min: Optional[int] = None
    delivery_days_max: Optional[int] = None
    main_image_url: Optional[str]
    image_urls: Optional[list]
    category: Optional[str]
    status: str
    remark: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductDetail(ProductOut):
    """商品详情（含匹配结果）"""
    pdd_matches: List[PddMatchOut] = []

    model_config = {"from_attributes": True}


from app.schemas.pdd_match import PddMatchOut  # noqa: E402
ProductDetail.model_rebuild()
