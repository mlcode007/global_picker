from sqlalchemy import (
    BigInteger, Column, DateTime, Enum, ForeignKey,
    Integer, JSON, SmallInteger, String, Text,
)
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class PhotoSearchTask(Base):
    __tablename__ = "photo_search_tasks"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    product_id = Column(BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    device_id = Column(String(64), nullable=True)
    status = Column(
        Enum(
            "queued", "dispatching", "running", "collecting",
            "parsing", "saving", "success", "failed",
            "retry_waiting", "cancelled",
        ),
        nullable=False, default="queued",
    )
    step = Column(String(32), nullable=True)
    source_image_url = Column(String(1024), nullable=True)
    device_image_path = Column(String(512), nullable=True)
    attempt_count = Column(TINYINT, nullable=False, default=0)
    max_attempts = Column(TINYINT, nullable=False, default=3)
    candidates_found = Column(Integer, nullable=False, default=0)
    candidates_saved = Column(Integer, nullable=False, default=0)
    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    elapsed_ms = Column(Integer, nullable=True)
    raw_result_json = Column(JSON, nullable=True)
    # 是否在结果页之后进入商品详情解析拼多多 H5 链接（关闭可缩短耗时）
    fetch_pdd_links = Column(TINYINT(1), nullable=False, server_default="1")
    # 单次任务最多入库的拼多多候选条数（与列表「单次最多」一致）
    max_candidates = Column(SmallInteger, nullable=False, default=4, server_default="4")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    product = relationship("Product", backref="photo_search_tasks")


class DeviceActionLog(Base):
    __tablename__ = "device_action_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(BigInteger, ForeignKey("photo_search_tasks.id", ondelete="CASCADE"), nullable=False)
    device_id = Column(String(64), nullable=False)
    step = Column(String(32), nullable=False)
    action = Column(String(128), nullable=False)
    success = Column(TINYINT(1), nullable=False, default=1)
    elapsed_ms = Column(Integer, nullable=True)
    screenshot_path = Column(String(512), nullable=True)
    xml_dump_path = Column(String(512), nullable=True)
    ocr_text = Column(Text, nullable=True)
    extra = Column(JSON, nullable=True)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    task = relationship("PhotoSearchTask", backref="action_logs")
