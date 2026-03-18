from sqlalchemy import Column, DateTime, Integer, Numeric, String
from sqlalchemy.sql import func
from app.database import Base


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    currency = Column(String(8), nullable=False, unique=True)
    rate_to_cny = Column(Numeric(10, 6), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
