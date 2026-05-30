from sqlalchemy import (
    BigInteger, Column, DateTime, Enum, ForeignKey,
    Integer, Numeric, String,
)
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Alibaba1688Match(Base):
    __tablename__ = "alibaba1688_matches"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    product_id = Column(BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    offer_id = Column(String(64), nullable=True)
    member_id = Column(String(64), nullable=True)
    title = Column(String(512), nullable=False, default="")
    main_image = Column(String(1024), nullable=True)
    images = Column(String(2048), nullable=True)
    last30_days_sales = Column(String(64), nullable=True)
    total_sales = Column(String(64), nullable=True)
    good_rates = Column(Numeric(5, 2), nullable=True)
    repurchase_rate = Column(String(32), nullable=True)
    tp_year = Column(Integer, nullable=True)
    free_return_in7d = Column(String(32), nullable=True)
    support_waybill = Column(String(256), nullable=True)
    price = Column(Numeric(12, 2), nullable=False, default=0)
    match_source = Column(
        Enum("image_search", "manual"),
        nullable=False,
        default="image_search",
    )
    is_confirmed = Column(TINYINT(1), nullable=False, default=0)
    is_primary = Column(TINYINT(1), nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    product = relationship("Product", back_populates="alibaba1688_matches")
