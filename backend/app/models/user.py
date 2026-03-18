from sqlalchemy import Column, DateTime, Enum, Integer, String
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), nullable=False, unique=True)
    password = Column(String(128), nullable=False)
    display_name = Column(String(64), nullable=False, default="")
    role = Column(Enum("admin", "editor", "viewer"), nullable=False, default="editor")
    is_active = Column(TINYINT(1), nullable=False, default=1)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
