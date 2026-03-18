from sqlalchemy import (
    BigInteger, Column, DateTime, Enum, Integer,
    JSON, Numeric, SmallInteger, String, Text,
)
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    crawl_task_id = Column(BigInteger, nullable=True)
    tiktok_url = Column(String(1024), nullable=False, unique=True)
    tiktok_product_id = Column(String(64), nullable=True)
    title = Column(String(512), nullable=False, default="")
    description = Column(Text, nullable=True)
    price = Column(Numeric(12, 2), nullable=False, default=0)
    currency = Column(String(8), nullable=False, default="PHP")
    price_cny = Column(Numeric(12, 2), nullable=True)
    sales_volume = Column(Integer, nullable=False, default=0)
    rating = Column(Numeric(3, 2), nullable=True)
    review_count = Column(Integer, nullable=False, default=0)
    stock_status = Column(TINYINT(1), nullable=False, default=1)
    region = Column(String(16), nullable=False, default="PH")
    shop_name = Column(String(256), nullable=True)
    shop_id = Column(String(64), nullable=True)
    original_price = Column(Numeric(12, 2), nullable=True)
    discount = Column(String(16), nullable=True)
    seller_location = Column(String(64), nullable=True)
    shipping_fee = Column(Numeric(12, 2), nullable=True)
    free_shipping = Column(TINYINT(1), nullable=True, default=0)
    delivery_days_min = Column(Integer, nullable=True)
    delivery_days_max = Column(Integer, nullable=True)
    main_image_url = Column(String(1024), nullable=True)
    image_urls = Column(JSON, nullable=True)
    category = Column(String(128), nullable=True)
    status = Column(
        Enum("pending", "selected", "abandoned"),
        nullable=False,
        default="pending",
    )
    remark = Column(String(512), nullable=True)
    is_deleted = Column(TINYINT(1), nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    pdd_matches = relationship("PddMatch", back_populates="product", cascade="all, delete-orphan")
    profit_records = relationship("ProfitRecord", back_populates="product", cascade="all, delete-orphan")
