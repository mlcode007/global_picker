from sqlalchemy import (
    BigInteger, Column, DateTime, Enum, Integer,
    JSON, String,
)
from sqlalchemy.sql import func
from app.database import Base


class Device(Base):
    __tablename__ = "device_pool"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(64), nullable=False, unique=True)
    device_name = Column(String(128), nullable=True)
    device_type = Column(
        Enum("real_phone", "cloud_phone"),
        nullable=False, default="real_phone",
    )
    android_version = Column(String(16), nullable=True)
    screen_width = Column(Integer, nullable=True)
    screen_height = Column(Integer, nullable=True)
    app_package = Column(String(128), nullable=False, default="com.xunmeng.pinduoduo")
    app_version = Column(String(32), nullable=True)
    status = Column(
        Enum("idle", "busy", "offline", "error"),
        nullable=False, default="idle",
    )
    current_task_id = Column(BigInteger, nullable=True)
    last_heartbeat = Column(DateTime, nullable=True)
    error_count = Column(Integer, nullable=False, default=0)
    capabilities = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
