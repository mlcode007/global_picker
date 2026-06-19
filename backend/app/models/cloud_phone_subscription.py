from sqlalchemy import Column, Integer, DateTime, Enum
from sqlalchemy.sql import func
from app.database import Base


class CloudPhoneSubscription(Base):
    """云手机订阅表"""
    __tablename__ = "cloud_phone_subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True, comment='用户ID')
    device_id = Column(Integer, nullable=True, comment='绑定的云手机设备ID，允许先购买后绑定')
    order_id = Column(Integer, nullable=True, comment='关联的支付订单ID')
    status = Column(Enum("active", "expired"), nullable=False, default="active", comment='订阅状态')
    started_at = Column(DateTime, server_default=func.now(), nullable=False, comment='开始时间')
    expires_at = Column(DateTime, nullable=True, comment='到期时间（未开通空位为 NULL）')
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
