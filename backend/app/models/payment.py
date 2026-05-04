from sqlalchemy import Column, Integer, String, DateTime, Numeric, Enum, Text, Index
from sqlalchemy.sql import func
from app.database import Base


class PaymentOrder(Base):
    """支付订单表"""
    __tablename__ = "payment_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True, comment='用户ID')
    out_trade_no = Column(String(64), nullable=False, unique=True, comment='商户订单号')
    trade_no = Column(String(64), nullable=True, comment='支付宝交易号')
    payment_method = Column(String(32), nullable=False, default='alipay', comment='支付方式')
    amount = Column(Numeric(10, 2), nullable=False, comment='支付金额（元）')
    points = Column(Integer, nullable=False, comment='获得积分数量')
    status = Column(
        Enum("pending", "paid", "closed", "failed"),
        nullable=False,
        default="pending",
        comment='订单状态'
    )
    subject = Column(String(256), nullable=False, comment='订单标题')
    qr_code = Column(Text, nullable=True, comment='二维码内容')
    paid_at = Column(DateTime, nullable=True, comment='支付完成时间')
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_user_id_status', 'user_id', 'status'),
        Index('idx_out_trade_no', 'out_trade_no'),
        Index('idx_created_at', 'created_at'),
    )
