from sqlalchemy import BigInteger, Column, DateTime, Enum, SmallInteger, Text, String
from sqlalchemy.sql import func
from app.database import Base


class CrawlTask(Base):
    __tablename__ = "crawl_tasks"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    url = Column(String(1024), nullable=False)
    status = Column(
        Enum("pending", "running", "done", "failed"),
        nullable=False,
        default="pending",
    )
    retry_count = Column(SmallInteger, nullable=False, default=0)
    error_msg = Column(Text, nullable=True)
    status_detail = Column(String(512), nullable=True)  # running 时细粒度提示，如验证码
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
