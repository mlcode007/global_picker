from sqlalchemy import Column, Integer, String, DateTime, Numeric, Enum, Index
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.sql import func
from app.database import Base


class DiscountCode(Base):
    """会员折扣码：管理员生成，按会员等级调整购买价格。"""
    __tablename__ = "discount_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(64), nullable=False, unique=True, comment='折扣码')
    tier = Column(
        Enum("basic", "pro"),
        nullable=False,
        comment='适用会员等级：基础版/专业版',
    )
    price = Column(Numeric(10, 2), nullable=False, comment='使用折扣码后的价格（元/月）')
    is_active = Column(TINYINT(1), nullable=False, default=1, comment='是否启用')
    status = Column(
        Enum("unused", "used"),
        nullable=False,
        default="unused",
        comment='使用状态：未使用/已使用（一次性）',
    )
    max_uses = Column(Integer, nullable=True, comment='最大可用次数，NULL 表示不限')
    used_count = Column(Integer, nullable=False, default=0, comment='已使用次数')
    expires_at = Column(DateTime, nullable=True, comment='折扣码有效期，NULL 表示长期有效')
    remark = Column(String(256), nullable=True, comment='备注')
    created_by = Column(Integer, nullable=True, comment='创建管理员ID')
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_code', 'code'),
        Index('idx_tier_active', 'tier', 'is_active'),
    )
