from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func
from app.database import Base


class UserCrawlConfig(Base):
    __tablename__ = "user_crawl_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, unique=True, index=True)
    tiktok_cookies = Column(Text, nullable=True, comment="TikTok Cookie JSON")
    tiktok_proxy = Column(String(256), nullable=True, comment="TikTok 代理地址")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
