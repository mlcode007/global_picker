from sqlalchemy import Column, DateTime, Enum, Integer, String, JSON, ForeignKey, Boolean
from sqlalchemy.sql import func
from app.database import Base


class CloudPhonePool(Base):
    """云手机池表 - 管理所有云手机资源"""
    __tablename__ = "cloud_phone_pool"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone_id = Column(String(64), nullable=False, unique=True, comment='云手机ID')
    phone_name = Column(String(128), nullable=True, comment='云手机名称')
    status = Column(
        Enum("available", "binding", "bound", "offline", "maintenance", "deleted", "timeo"),
        nullable=False,
        default="available",
        comment='状态: available-可用, binding-绑定中, bound-已绑定, offline-离线, maintenance-维护中, deleted-已删除, timeo-ADB超时'
    )
    created_by = Column(Integer, nullable=True, comment="创建用户ID")
    region = Column(String(32), nullable=False, default="cn-jsha-cloudphone-3", comment='地域')
    instance_type = Column(String(64), nullable=True, comment='实例类型')
    spec = Column(JSON, nullable=True, comment='规格信息（CPU、内存、存储等）')
    adb_host_port = Column(String(64), nullable=True, comment='ADB连接端口')
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class UserCloudPhone(Base):
    """用户云手机绑定表 - 记录用户与云手机的绑定关系"""
    __tablename__ = "user_cloud_phone"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, comment='用户ID')
    phone_id = Column(String(64), nullable=False, comment='云手机ID')
    bind_at = Column(DateTime, nullable=False, default=func.now(), comment='绑定时间')
    unbind_at = Column(DateTime, nullable=True, comment='解绑时间（软删除）')
    is_active = Column(Boolean, nullable=False, default=True, comment='是否激活')
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
