from sqlalchemy import Column, DateTime, Enum, Integer, String
from sqlalchemy.dialects.mysql import BIGINT, TINYINT
from sqlalchemy.sql import func
from app.database import Base


class SmsVerification(Base):
    __tablename__ = "sms_verification"

    id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    phone = Column(String(20), nullable=False, index=True)
    code = Column(String(6), nullable=False)
    purpose = Column(
        Enum("register", "login", "reset_password"),
        nullable=False,
        default="login",
    )
    is_used = Column(TINYINT(1), nullable=False, default=0)
    expired_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
