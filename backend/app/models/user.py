from sqlalchemy import Column, DateTime, Enum, Integer, String, JSON
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), nullable=True, unique=True)
    phone = Column(String(20), nullable=True, unique=True)
    password = Column(String(128), nullable=True)
    display_name = Column(String(64), nullable=False, default="")
    company_name = Column(String(128), nullable=False, default="")
    contact_name = Column(String(64), nullable=False, default="")
    business_type = Column(
        Enum("cross_border", "wholesale", "retail", "other"),
        nullable=False,
        default="cross_border",
    )
    target_regions = Column(JSON, nullable=True)
    avatar = Column(String(512), nullable=True)
    role = Column(Enum("admin", "editor", "viewer"), nullable=False, default="editor")
    is_active = Column(TINYINT(1), nullable=False, default=1)
    last_login = Column(DateTime, nullable=True)
    preferences = Column(JSON, nullable=True, comment="用户偏好 JSON，如导出列配置")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
