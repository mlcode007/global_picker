from sqlalchemy import (
    BigInteger, Column, DateTime, Enum, ForeignKey,
    Integer, Numeric, String,
)
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class PddMatch(Base):
    __tablename__ = "pdd_matches"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    product_id = Column(BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    pdd_product_id = Column(String(64), nullable=True)
    pdd_title = Column(String(512), nullable=False, default="")
    pdd_price = Column(Numeric(12, 2), nullable=False, default=0)
    pdd_original_price = Column(Numeric(12, 2), nullable=True)
    pdd_sales_volume = Column(Integer, nullable=True)
    pdd_shop_name = Column(String(256), nullable=True)
    pdd_shop_id = Column(String(64), nullable=True)
    pdd_image_url = Column(String(1024), nullable=True)
    pdd_product_url = Column(String(1024), nullable=True)
    match_source = Column(
        Enum("image_search", "keyword_search", "manual"),
        nullable=False,
        default="image_search",
    )
    match_confidence = Column(Numeric(5, 4), nullable=True)
    is_confirmed = Column(TINYINT(1), nullable=False, default=0)
    is_primary = Column(TINYINT(1), nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    product = relationship("Product", back_populates="pdd_matches")
