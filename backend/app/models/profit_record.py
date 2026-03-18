from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ProfitRecord(Base):
    __tablename__ = "profit_records"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    product_id = Column(BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    pdd_match_id = Column(BigInteger, nullable=True)
    tiktok_price_cny = Column(Numeric(12, 2), nullable=False)
    pdd_price_cny = Column(Numeric(12, 2), nullable=False)
    logistics_cost = Column(Numeric(12, 2), nullable=False, default=0)
    platform_fee_rate = Column(Numeric(5, 4), nullable=False, default=0)
    platform_fee = Column(Numeric(12, 2), nullable=False, default=0)
    other_cost = Column(Numeric(12, 2), nullable=False, default=0)
    profit = Column(Numeric(12, 2), nullable=False)
    profit_rate = Column(Numeric(7, 4), nullable=False)
    exchange_rate = Column(Numeric(10, 4), nullable=True)
    note = Column(String(512), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    product = relationship("Product", back_populates="profit_records")
