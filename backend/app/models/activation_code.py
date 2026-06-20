"""
激活码模型 - 用于直播/线下销售场景
管理员生成激活码，用户输入激活码后自动注册并开通会员
"""
import random
import string
from sqlalchemy import Column, DateTime, Integer, String, Boolean, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


def generate_activation_code(length: int = 12) -> str:
    """生成激活码：4组3位大写字母+数字，如 AB3-CD4-EF5-GH6"""
    alphabet = string.ascii_uppercase.replace('O', '').replace('I', '') + string.digits
    groups = []
    for _ in range(4):
        group = "".join(random.choices(alphabet, k=length // 4))
        groups.append(group)
    return "-".join(groups)


class ActivationCode(Base):
    __tablename__ = "activation_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), nullable=False, unique=True, index=True, comment="激活码")
    tier = Column(String(20), nullable=False, default="basic", comment="开通的会员等级: basic/pro")
    duration_months = Column(Integer, nullable=False, default=1, comment="有效期（月）")
    max_uses = Column(Integer, nullable=False, default=1, comment="最大使用次数")
    used_count = Column(Integer, nullable=False, default=0, comment="已使用次数")
    is_active = Column(Boolean, nullable=False, default=True, comment="是否启用")
    remark = Column(String(256), nullable=True, comment="备注（如：直播299基础版）")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="创建人")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=True, comment="激活码过期时间")
