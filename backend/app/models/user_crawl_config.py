from sqlalchemy import Column, DateTime, Integer, JSON, String, Text
from sqlalchemy.sql import func
from app.database import Base


class UserCrawlConfig(Base):
    __tablename__ = "user_crawl_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, unique=True, index=True)
    tiktok_cookies = Column(Text, nullable=True, comment="TikTok Cookie JSON")
    tiktok_proxy = Column(String(256), nullable=True, comment="TikTok 默认代理地址（无分国家配置时回退使用）")
    # 分国家代理：形如 {"PH": "http://...", "MY": "socks5://...", "ID": ""}
    region_proxies = Column(JSON, nullable=True, comment="分国家代理配置，key 为 region code（PH/MY/TH/SG/ID/VN...）")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
