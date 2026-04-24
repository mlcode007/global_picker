from sqlalchemy import Column, Integer, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


class UserQuota(Base):
    """用户每日采集配额表"""
    __tablename__ = "user_quotas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True, comment='用户ID')
    quota_date = Column(DateTime, nullable=False, index=True, comment='配额日期（UTC）')
    used_count = Column(Integer, nullable=False, default=0, comment='已使用数量')
    daily_limit = Column(Integer, nullable=False, default=10000, comment='每日配额上限')
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class CollectionHistory(Base):
    """采集历史记录表"""
    __tablename__ = "collection_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True, comment='用户ID')
    product_url = Column(Text, nullable=True, comment='商品URL')
    product_id = Column(Integer, nullable=True, comment='关联商品ID')
    collected_at = Column(DateTime, server_default=func.now(), nullable=False, comment='采集时间')
