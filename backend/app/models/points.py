from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.sql import func
from app.database import Base


class UserPoints(Base):
    """用户积分表"""
    __tablename__ = "user_points"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, unique=True, comment='用户ID')
    points = Column(Integer, nullable=False, default=0, comment='当前积分')
    total_earned = Column(Integer, nullable=False, default=0, comment='总获取积分')
    total_consumed = Column(Integer, nullable=False, default=0, comment='总消耗积分')
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class PointsTransaction(Base):
    """积分交易记录表"""
    __tablename__ = "points_transaction"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, comment='用户ID')
    type = Column(Enum("earn", "consume"), nullable=False, comment='交易类型')
    amount = Column(Integer, nullable=False, comment='积分数量')
    reason = Column(Text, nullable=False, comment='交易原因')
    related_id = Column(String(128), nullable=True, comment='关联ID')
    created_at = Column(DateTime, server_default=func.now(), nullable=False)