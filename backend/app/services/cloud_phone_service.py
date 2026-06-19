"""
云手机管理器
- 云手机池管理
- 用户绑定管理
- 资源分配与回收
- 自动扩容机制
"""
from __future__ import annotations

import logging
import math
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.models.cloud_phone import CloudPhonePool, UserCloudPhone
from app.models.user import User
from app.models.cloud_phone_subscription import CloudPhoneSubscription
from app.util.chinac.chinac_open_api import ChinacOpenApi
from app.util.chinac_utils import cloud_phone_create
from app.core.membership import CLOUD_PHONE_MAX, CLOUD_PHONE_PRICE, CLOUD_PHONE_PERIOD_DAYS, CLOUD_PHONE_RENEW_WARN_DAYS

logger = logging.getLogger(__name__)


class CloudPhoneQuotaExceeded(Exception):
    """云手机订阅额度不足或开通受限。"""
    pass


class CloudPhoneProvisionRateLimited(CloudPhoneQuotaExceeded):
    """开通操作过于频繁。"""
    pass


class CloudPhoneManager:
    """云手机管理器 - 负责云手机资源的全生命周期管理"""
    
    # 阈值配置
    MIN_AVAILABLE_POOL = 3  # 最小可用池数量
    MAX_AUTO_SCALE = 10     # 最大自动扩容数量
    AUTO_SCALE_THRESHOLD = 0.3  # 自动扩容触发阈值（可用率低于30%）
    MIN_PROVISION_INTERVAL_SEC = 60  # 同一用户两次开通最小间隔（秒）
    
    def __init__(self, db: Session):
        self.db = db
        self.api = ChinacOpenApi()

    @staticmethod
    def _utc_now_naive() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def _active_subscription_filter(now: datetime):
        """有效订阅：active 且未到期（空位 expires_at 为 NULL）。"""
        return (
            CloudPhoneSubscription.status == "active",
            or_(
                CloudPhoneSubscription.expires_at.is_(None),
                CloudPhoneSubscription.expires_at > now,
            ),
        )
    
    # ── 云手机池管理 ──────────────────────────────────────────
    
    def add_to_pool(self, phone_id: str, phone_name: str = None, 
                    instance_type: str = None, spec: Dict = None, created_by: int = None) -> CloudPhonePool:
        """将云手机加入资源池"""
        phone = CloudPhonePool(
            phone_id=phone_id,
            phone_name=phone_name,
            status="available",
            instance_type=instance_type,
            spec=spec,
            created_by=created_by
        )
        self.db.add(phone)
        self.db.commit()
        self.db.refresh(phone)
        logger.info("Cloud phone %s added to pool", phone_id)
        return phone
    
    def remove_from_pool(self, phone_id: str, user_id: int) -> bool:
        """从资源池软删除云手机（仅标记 deleted，仍占用订阅额度）。"""
        phone = self.db.query(CloudPhonePool).filter(CloudPhonePool.phone_id == phone_id).first()
        if not phone:
            return False
        if phone.created_by is not None and phone.created_by != user_id:
            logger.warning(
                "User %d denied remove phone %s (owner=%s)",
                user_id, phone_id, phone.created_by,
            )
            return False
        phone.status = "deleted"
        phone.updated_at = datetime.now()
        self.db.commit()
        logger.info("Cloud phone %s marked deleted by user %d", phone_id, user_id)
        return True
    
    def update_pool_status(self, phone_id: str, status: str) -> bool:
        """更新云手机在池中的状态"""
        phone = self.db.query(CloudPhonePool).filter(CloudPhonePool.phone_id == phone_id).first()
        if phone:
            phone.status = status
            phone.updated_at = datetime.now()
            self.db.commit()
            logger.info("Cloud phone %s status updated to %s", phone_id, status)
            return True
        return False
    
    def get_available_count(self) -> int:
        """获取可用云手机数量"""
        from sqlalchemy import func
        return self.db.query(func.count(CloudPhonePool.id)).filter(
            CloudPhonePool.status == "available"
        ).scalar() or 0
    
    def list_available_phones(self, limit: int = 10) -> List[CloudPhonePool]:
        """获取可用云手机列表"""
        from sqlalchemy.orm import load_only
        from sqlalchemy import inspect
        inspector = inspect(CloudPhonePool)
        has_adb_host_port = 'adb_host_port' in [c.name for c in inspector.columns]
        
        # 构建要加载的字段列表
        load_fields = [
            'id',
            'phone_id',
            'phone_name',
            'status',
            'created_by',
            'region',
            'instance_type',
            'spec',
            'created_at',
            'updated_at'
        ]
        
        if has_adb_host_port:
            load_fields.append('adb_host_port')
        
        # 使用 load_only 来指定只加载这些字段
        return self.db.query(CloudPhonePool).options(
            load_only(*load_fields)
        ).filter(
            CloudPhonePool.status == "available"
        ).limit(limit).all()
    
    def list_all_phones(self) -> List[CloudPhonePool]:
        """获取所有云手机"""
        from sqlalchemy.orm import load_only
        from sqlalchemy import inspect
        inspector = inspect(CloudPhonePool)
        has_adb_host_port = 'adb_host_port' in [c.name for c in inspector.columns]
        
        # 构建要加载的字段列表
        load_fields = [
            'id',
            'phone_id',
            'phone_name',
            'status',
            'created_by',
            'region',
            'instance_type',
            'spec',
            'created_at',
            'updated_at'
        ]
        
        if has_adb_host_port:
            load_fields.append('adb_host_port')
        
        # 使用 load_only 来指定只加载这些字段
        return self.db.query(CloudPhonePool).options(
            load_only(*load_fields)
        ).all()
    
    # ── 用户绑定管理 ──────────────────────────────────────────
    
    def bind_to_user(self, user_id: int, phone_id: str) -> Optional[UserCloudPhone]:
        """将云手机绑定给用户"""
        # 检查用户是否已有云手机
        existing = self.db.query(UserCloudPhone).filter(
            UserCloudPhone.user_id == user_id,
            UserCloudPhone.is_active == True
        ).first()
        
        if existing:
            logger.warning("User %d already has cloud phone: %s", user_id, existing.phone_id)
            return None
        
        # 获取云手机信息
        from sqlalchemy.orm import load_only
        from sqlalchemy import inspect
        inspector = inspect(CloudPhonePool)
        has_adb_host_port = 'adb_host_port' in [c.name for c in inspector.columns]
        
        # 构建要加载的字段列表
        load_fields = [
            'id',
            'phone_id',
            'phone_name',
            'status',
            'created_by',
            'region',
            'instance_type',
            'spec',
            'created_at',
            'updated_at'
        ]
        
        if has_adb_host_port:
            load_fields.append('adb_host_port')
        
        # 使用 load_only 来指定只加载这些字段
        phone = self.db.query(CloudPhonePool).options(
            load_only(*load_fields)
        ).filter(
            CloudPhonePool.phone_id == phone_id
        ).first()
        
        if not phone:
            logger.error("Cloud phone %s not found in pool", phone_id)
            return None

        if phone.created_by is not None and phone.created_by != user_id:
            logger.warning(
                "User %d cannot bind phone %s (owner=%s)",
                user_id, phone_id, phone.created_by,
            )
            return None
        
        if phone.status != "available":
            logger.error("Cloud phone %s is not available (status: %s)", phone_id, phone.status)
            return None
        
        # 更新云手机状态
        phone.status = "bound"
        phone.updated_at = datetime.now()
        
        # 创建绑定关系
        binding = UserCloudPhone(
            user_id=user_id,
            phone_id=phone_id
        )
        self.db.add(binding)
        self.db.commit()
        self.db.refresh(binding)
        
        logger.info("Cloud phone %s bound to user %d", phone_id, user_id)
        return binding
    
    def unbind_from_user(self, user_id: int, force: bool = False) -> bool:
        """解绑用户的云手机"""
        binding = self.db.query(UserCloudPhone).filter(
            UserCloudPhone.user_id == user_id,
            UserCloudPhone.is_active == True
        ).first()
        
        if not binding:
            logger.warning("No cloud phone bound to user %d", user_id)
            return False
        
        phone_id = binding.phone_id
        
        # 更新绑定关系（软删除）
        binding.is_active = False
        binding.unbind_at = datetime.now()
        binding.updated_at = datetime.now()
        
        # 更新云手机状态
        # 直接查询整个对象，因为我们只需要更新状态
        phone = self.db.query(CloudPhonePool).filter(
            CloudPhonePool.phone_id == phone_id
        ).first()
        
        if phone:
            if force:
                phone.status = "available"
            else:
                # 正常解绑后设置为offline，等待检查后再设为available
                phone.status = "offline"
            phone.updated_at = datetime.now()
        
        self.db.commit()
        logger.info("Cloud phone %s unbound from user %d", phone_id, user_id)
        return True
    
    def get_user_phone(self, user_id: int) -> Optional[UserCloudPhone]:
        """获取用户的云手机绑定信息"""
        return self.db.query(UserCloudPhone).filter(
            UserCloudPhone.user_id == user_id,
            UserCloudPhone.is_active == True
        ).first()
    
    def get_user_phone_id(self, user_id: int) -> Optional[str]:
        """获取用户的云手机ID"""
        binding = self.get_user_phone(user_id)
        return binding.phone_id if binding else None
    
    def get_phone_user(self, phone_id: str) -> Optional[User]:
        """获取使用指定云手机的用户"""
        binding = self.db.query(UserCloudPhone).filter(
            UserCloudPhone.phone_id == phone_id,
            UserCloudPhone.is_active == True
        ).first()
        
        if binding:
            return self.db.query(User).filter(User.id == binding.user_id).first()
        return None
    
    # ── 资源分配策略 ──────────────────────────────────────────
    
    def acquire_phone_for_user(self, user_id: int) -> Optional[UserCloudPhone]:
        """
        为用户分配云手机（核心方法）
        策略：
        1. 检查用户是否已有云手机，如果有则返回错误
        2. 检查用户是否有活跃的云手机订阅
        3. 从资源池分配空闲云手机
        4. 触发自动扩容（如果需要）
        """
        # 检查用户是否已有云手机
        existing = self.get_user_phone(user_id)
        if existing:
            logger.warning("User %d already has cloud phone: %s, cannot acquire another one", user_id, existing.phone_id)
            return None
        
        # 检查用户是否有有效云手机订阅（订阅制，不再扣积分）
        active_count = self._count_active_subscriptions(user_id)
        bound_count = self.db.query(UserCloudPhone).filter(
            UserCloudPhone.user_id == user_id,
        ).count()
        
        if bound_count >= active_count:
            logger.warning("User %d has no spare subscription (active=%d, bound=%d)", user_id, active_count, bound_count)
            return None
        
        # 从当前用户的资源池分配
        available = self._try_acquire_from_pool(user_id)
        if available:
            binding = self.bind_to_user(user_id, available.phone_id)
            if binding:
                return binding
            else:
                logger.warning("Failed to bind cloud phone to user %d", user_id)
                return None
        
        # 触发自动扩容（消耗订阅额度）
        try:
            new_phones = self.provision_phones(1, user_id)
            if new_phones:
                time.sleep(2)
                binding = self.bind_to_user(user_id, new_phones[0].phone_id)
                if binding:
                    return binding
                logger.warning("Failed to bind auto-scaled phone to user %d", user_id)
        except CloudPhoneQuotaExceeded:
            logger.warning("User %d has no subscription slot for auto provision", user_id)
        
        # 没有可用云手机
        logger.warning("No available cloud phone for user %d", user_id)
        return None
    
    def _try_acquire_from_pool(self, user_id: int) -> Optional[CloudPhonePool]:
        """尝试从当前用户的资源池获取可用云手机。"""
        from sqlalchemy.orm import load_only
        from sqlalchemy import inspect
        inspector = inspect(CloudPhonePool)
        has_adb_host_port = 'adb_host_port' in [c.name for c in inspector.columns]
        
        # 构建要加载的字段列表
        load_fields = [
            'id',
            'phone_id',
            'phone_name',
            'status',
            'created_by',
            'region',
            'instance_type',
            'spec',
            'created_at',
            'updated_at'
        ]
        
        if has_adb_host_port:
            load_fields.append('adb_host_port')
        
        # 使用 load_only 来指定只加载这些字段
        phone = self.db.query(CloudPhonePool).options(
            load_only(*load_fields)
        ).filter(
            CloudPhonePool.status == "available",
            CloudPhonePool.created_by == user_id,
        ).with_for_update(skip_locked=True).first()
        
        if phone:
            phone.status = "binding"
            phone.updated_at = datetime.now()
            self.db.commit()
        
        return phone
    
    def _should_auto_scale(self) -> bool:
        """判断是否需要自动扩容"""
        from sqlalchemy import func
        total = self.db.query(func.count(CloudPhonePool.id)).scalar() or 0
        available = self.get_available_count()
        
        if total == 0:
            return True
        
        available_rate = available / total
        return available_rate < self.AUTO_SCALE_THRESHOLD
    
    def _auto_scale(self, count: int = None, user_id: int = None) -> List[CloudPhonePool]:
        """自动扩容云手机"""
        # 安全检查：限制扩容数量
        count = count or min(self.MAX_AUTO_SCALE, self.MIN_AVAILABLE_POOL)
        count = min(count, self.MAX_AUTO_SCALE)  # 确保不超过最大限制
        
        if count <= 0:
            logger.warning("Invalid scale count: %d", count)
            return []
        
        created = []
        for i in range(count):
            try:
                # 生成唯一的手机名称，防止重复
                phone_name = f"auto-scale-{int(time.time())}-{i}"
                
                # 使用 chinac_utils 中的 cloud_phone_create 函数创建云手机
                logger.info("Creating cloud phone %d with name: %s", i, phone_name)
                response = cloud_phone_create()
                
                logger.info("Cloud phone create response: %s", response)
                
                # 检查响应格式
                if not response:
                    logger.error("No response from cloud_phone_create")
                    continue
                
                if 'data' not in response:
                    logger.error("No 'data' field in response: %s", response)
                    continue
                
                data = response['data']
                logger.info("Cloud phone create data: %s", data)
                
                if not data:
                    logger.error("Empty data in response")
                    continue
                
                if 'ResourceIds' not in data:
                    logger.error("No 'ResourceIds' field in data: %s", data)
                    continue
                
                phone_ids = data['ResourceIds']
                logger.info("Cloud phone ResourceIds: %s", phone_ids)
                
                if not phone_ids or len(phone_ids) == 0:
                    logger.error("Empty or invalid ResourceIds: %s", phone_ids)
                    continue
                
                phone_id = phone_ids[0]
                # 验证返回的ID格式
                if not phone_id or not phone_id.startswith('cp-'):
                    logger.error("Invalid cloud phone ID: %s", phone_id)
                    continue
                
                # 添加到资源池
                try:
                    phone = self.add_to_pool(
                        phone_id=phone_id,
                        phone_name=phone_name,
                        instance_type="ci.g5.large",
                        created_by=user_id
                    )
                    
                    created.append(phone)
                    logger.info("Successfully created cloud phone: %s", phone_id)
                except Exception as db_error:
                    # 检查是否是唯一性约束错误（phone_id已存在）
                    if "unique" in str(db_error).lower() or "duplicate" in str(db_error).lower():
                        logger.warning("Cloud phone %s already exists in pool, skipping", phone_id)
                        # 查询已存在的记录
                        existing_phone = self.db.query(CloudPhonePool).filter(
                            CloudPhonePool.phone_id == phone_id
                        ).first()
                        if existing_phone:
                            created.append(existing_phone)
                            logger.info("Using existing cloud phone: %s", phone_id)
                    else:
                        raise db_error
                
                # 防止批量创建导致费用过高，每创建一台延迟1秒
                time.sleep(1)
                
            except Exception as e:
                logger.error("Failed to create cloud phone %d: %s", i, str(e))
                # 发生错误时立即停止，避免连续失败导致的费用问题
                break
        
        if created:
            logger.info("Auto scaled %d cloud phones", len(created))
        
        return created
    
    # ── 状态检查与维护 ──────────────────────────────────────────
    
    def check_phone_health(self, phone_id: str) -> bool:
        """检查云手机健康状态"""
        try:
            from app.util.chinac_utils import (
                cloud_phone_check_status,
                cloud_phone_describe_phone,
                is_cloud_phone_not_found,
            )

            # 先查云端是否存在，不存在则直接标记离线，跳过 ADB 慢路径
            try:
                device_info = cloud_phone_describe_phone(phone_id)
            except Exception as describe_err:
                logger.warning("DescribeCloudPhone 失败 %s: %s", phone_id, describe_err)
                device_info = None

            if device_info is not None and is_cloud_phone_not_found(device_info):
                logger.info("Cloud phone %s not found in cloud, mark deleted", phone_id)
                self._apply_health_status(phone_id, "deleted", adb_host_port=None)
                return False

            adb_status = cloud_phone_check_status(phone_id, device_info=device_info)
            logger.info(f"ADB status check result: {adb_status}")

            adb_host_port = None
            if adb_status['code'] != -1 and device_info and 'data' in device_info:
                basic_info = device_info['data'].get('BasicInfo') or {}
                adb_host_port = basic_info.get('AdbHostPort')
                if not adb_host_port and 'NetInfo' in device_info['data']:
                    outer_ip = device_info['data']['NetInfo'].get('OuterIp')
                    if outer_ip:
                        adb_host_port = f"{outer_ip}:5555"

            if adb_status['code'] == 0:
                self._apply_health_status(phone_id, "available", adb_host_port)
            elif adb_status['code'] == -1:
                self._apply_health_status(phone_id, "deleted", adb_host_port)
            elif adb_status['code'] == -3:
                self._apply_health_status(phone_id, "timeo", adb_host_port)
            else:
                self._apply_health_status(phone_id, "offline", adb_host_port)

            is_healthy = adb_status['code'] == 0
            logger.info(
                "Cloud phone %s health check result: %s (ADB status: %s)",
                phone_id,
                'healthy' if is_healthy else 'unhealthy',
                adb_status['message'],
            )
            return is_healthy

        except Exception as e:
            logger.error("Failed to check cloud phone %s health: %s", phone_id, str(e))
            return False

    def _apply_health_status(self, phone_id: str, status: str, adb_host_port: Optional[str] = None) -> None:
        """根据健康检查结果更新池内设备状态。"""
        phone = self.db.query(CloudPhonePool).filter(
            CloudPhonePool.phone_id == phone_id
        ).first()
        if not phone:
            return
        try:
            from sqlalchemy import inspect
            inspector = inspect(CloudPhonePool)
            has_adb_host_port = 'adb_host_port' in [c.name for c in inspector.columns]
            if has_adb_host_port and adb_host_port:
                phone.adb_host_port = adb_host_port
            phone.status = status
            phone.updated_at = datetime.now()
            self.db.commit()
            logger.info("Updated cloud phone %s status to %s", phone_id, status)
        except Exception as db_error:
            logger.error("Failed to update cloud phone %s in database: %s", phone_id, db_error)
            self.db.rollback()
    
    def recover_offline_phones(self) -> int:
        """恢复离线云手机"""
        from sqlalchemy.orm import load_only
        from sqlalchemy import inspect
        inspector = inspect(CloudPhonePool)
        has_adb_host_port = 'adb_host_port' in [c.name for c in inspector.columns]
        
        # 构建要加载的字段列表
        load_fields = [
            'id',
            'phone_id',
            'phone_name',
            'status',
            'created_by',
            'region',
            'instance_type',
            'spec',
            'created_at',
            'updated_at'
        ]
        
        if has_adb_host_port:
            load_fields.append('adb_host_port')
        
        # 使用 load_only 来指定只加载这些字段
        offline_phones = self.db.query(CloudPhonePool).options(
            load_only(*load_fields)
        ).filter(
            CloudPhonePool.status == "offline"
        ).all()
        
        recovered = 0
        for phone in offline_phones:
            if self.check_phone_health(phone.phone_id):
                phone.status = "available"
                phone.updated_at = datetime.now()
                recovered += 1
                logger.info("Cloud phone %s recovered to available", phone.phone_id)
        
        if recovered > 0:
            self.db.commit()
        
        return recovered
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """获取资源池统计信息"""
        from sqlalchemy import func
        total = self.db.query(func.count(CloudPhonePool.id)).scalar() or 0
        available = self.get_available_count()
        bound = self.db.query(func.count(CloudPhonePool.id)).filter(
            CloudPhonePool.status == "bound"
        ).scalar() or 0
        offline = self.db.query(func.count(CloudPhonePool.id)).filter(
            CloudPhonePool.status.in_(["offline", "timeo", "deleted", "maintenance"])
        ).scalar() or 0
        maintenance = self.db.query(func.count(CloudPhonePool.id)).filter(
            CloudPhonePool.status == "maintenance"
        ).scalar() or 0
        
        return {
            "total": total,
            "available": available,
            "bound": bound,
            "offline": offline,
            "maintenance": maintenance,
            "available_rate": available / total if total > 0 else 0
        }
    
    # ── 扩容接口（供外部调用）──────────────────────────────────────

    def _count_provisioned_active(self, user_id: int) -> int:
        """展示用已开通数：不含 deleted。"""
        from sqlalchemy import func
        return self.db.query(func.count(CloudPhonePool.id)).filter(
            CloudPhonePool.created_by == user_id,
            CloudPhonePool.status != "deleted",
        ).scalar() or 0

    def _count_provisioned_total(self, user_id: int) -> int:
        """额度占用总数：含 deleted，防止标记删除后重复开通。"""
        from sqlalchemy import func
        return self.db.query(func.count(CloudPhonePool.id)).filter(
            CloudPhonePool.created_by == user_id,
        ).scalar() or 0

    def _count_active_subscriptions(self, user_id: int) -> int:
        now = self._utc_now_naive()
        status_filter, expiry_filter = self._active_subscription_filter(now)
        return self.db.query(func.count(CloudPhoneSubscription.id)).filter(
            CloudPhoneSubscription.user_id == user_id,
            status_filter,
            expiry_filter,
        ).scalar() or 0

    def _count_unbound_slots(self, user_id: int) -> int:
        """可开通空位数：已购未绑定且未写 expires_at。"""
        now = self._utc_now_naive()
        status_filter, expiry_filter = self._active_subscription_filter(now)
        return self.db.query(func.count(CloudPhoneSubscription.id)).filter(
            CloudPhoneSubscription.user_id == user_id,
            status_filter,
            expiry_filter,
            CloudPhoneSubscription.device_id.is_(None),
            CloudPhoneSubscription.expires_at.is_(None),
        ).scalar() or 0

    def _build_quota(
        self,
        subscription_count: int,
        provisioned_active: int,
        provisioned_total: int,
        unbound_slots: int,
    ) -> Dict[str, Any]:
        capped_subscription = min(subscription_count, CLOUD_PHONE_MAX)
        available_slots = min(unbound_slots, max(0, CLOUD_PHONE_MAX - provisioned_active))
        return {
            "subscription_count": subscription_count,
            "provisioned_count": provisioned_active,
            "provisioned_total": provisioned_total,
            "available_slots": available_slots,
            "max": CLOUD_PHONE_MAX,
            "price": CLOUD_PHONE_PRICE,
            "period_days": CLOUD_PHONE_PERIOD_DAYS,
            "renew_warn_days": CLOUD_PHONE_RENEW_WARN_DAYS,
            "over_limit": provisioned_active > subscription_count,
        }

    def get_subscription_quota(self, user_id: int) -> Dict[str, Any]:
        """订阅额度：查询前懒处理到期订阅。"""
        from app.services.cloud_phone_expiry_service import expire_due_subscriptions

        expire_due_subscriptions(self.db, user_id=user_id)
        subscription_count = self._count_active_subscriptions(user_id)
        provisioned_active = self._count_provisioned_active(user_id)
        provisioned_total = self._count_provisioned_total(user_id)
        unbound_slots = self._count_unbound_slots(user_id)
        return self._build_quota(
            subscription_count, provisioned_active, provisioned_total, unbound_slots
        )

    def _assert_provision_allowed(self, user_id: int, count: int) -> Dict[str, Any]:
        """在事务锁内校验开通额度与频率。"""
        last = (
            self.db.query(CloudPhonePool)
            .filter(CloudPhonePool.created_by == user_id)
            .order_by(CloudPhonePool.created_at.desc())
            .first()
        )
        if last and last.created_at:
            created_ts = last.created_at.timestamp() if hasattr(last.created_at, 'timestamp') else 0
            elapsed = time.time() - created_ts
            if elapsed < self.MIN_PROVISION_INTERVAL_SEC:
                wait = int(self.MIN_PROVISION_INTERVAL_SEC - elapsed)
                raise CloudPhoneProvisionRateLimited(f"操作过于频繁，请 {max(wait, 1)} 秒后再试")

        subscription_count = self._count_active_subscriptions(user_id)
        provisioned_active = self._count_provisioned_active(user_id)
        provisioned_total = self._count_provisioned_total(user_id)
        unbound_slots = self._count_unbound_slots(user_id)
        quota = self._build_quota(
            subscription_count, provisioned_active, provisioned_total, unbound_slots
        )

        if count > quota["available_slots"]:
            raise CloudPhoneQuotaExceeded(
                f"可开通额度不足：已订阅 {subscription_count} 台，"
                f"已开通 {provisioned_active} 台，可开通 {quota['available_slots']} 台"
            )
        if provisioned_active + count > CLOUD_PHONE_MAX:
            raise CloudPhoneQuotaExceeded(f"每用户最多开通 {CLOUD_PHONE_MAX} 台云手机")
        return quota

    def _bind_subscriptions_to_phones(self, user_id: int, phones: List[CloudPhonePool]) -> None:
        """将新开通实例关联到尚未绑定设备的活跃空位订阅，并写入到期时间。"""
        if not phones:
            return
        now = self._utc_now_naive()
        expires_at = now + timedelta(days=CLOUD_PHONE_PERIOD_DAYS)
        unbound = (
            self.db.query(CloudPhoneSubscription)
            .filter(
                CloudPhoneSubscription.user_id == user_id,
                CloudPhoneSubscription.status == "active",
                CloudPhoneSubscription.device_id.is_(None),
                CloudPhoneSubscription.expires_at.is_(None),
            )
            .order_by(CloudPhoneSubscription.id)
            .limit(len(phones))
            .all()
        )
        for phone, sub in zip(phones, unbound):
            sub.device_id = phone.id
            sub.started_at = now
            sub.expires_at = expires_at
        if unbound:
            self.db.commit()

    def attach_pool_expiry_info(self, user_id: int, items: List[Dict[str, Any]]) -> None:
        """为池列表项附加到期/续费信息。"""
        if not items:
            return
        phone_ids = [item["phone_id"] for item in items if item.get("phone_id")]
        if not phone_ids:
            return

        pools = (
            self.db.query(CloudPhonePool)
            .filter(
                CloudPhonePool.phone_id.in_(phone_ids),
                CloudPhonePool.created_by == user_id,
            )
            .all()
        )
        pool_by_phone = {p.phone_id: p for p in pools}
        pool_ids = [p.id for p in pools]
        if not pool_ids:
            return

        subs = (
            self.db.query(CloudPhoneSubscription)
            .filter(
                CloudPhoneSubscription.user_id == user_id,
                CloudPhoneSubscription.device_id.in_(pool_ids),
            )
            .order_by(CloudPhoneSubscription.id.desc())
            .all()
        )
        sub_by_device: Dict[int, CloudPhoneSubscription] = {}
        for sub in subs:
            if sub.device_id not in sub_by_device:
                sub_by_device[sub.device_id] = sub

        now = self._utc_now_naive()
        for item in items:
            pool = pool_by_phone.get(item.get("phone_id"))
            if not pool:
                continue
            sub = sub_by_device.get(pool.id)
            if not sub:
                item.update({
                    "expires_at": None,
                    "days_remaining": None,
                    "renewable": False,
                    "subscription_status": None,
                })
                continue

            item["subscription_status"] = sub.status
            if sub.expires_at:
                item["expires_at"] = sub.expires_at.isoformat()
                delta_sec = (sub.expires_at - now).total_seconds()
                item["days_remaining"] = max(0, math.ceil(delta_sec / 86400))
                item["renewable"] = (
                    sub.status == "active"
                    and sub.expires_at > now
                    and item.get("status") != "deleted"
                )
            else:
                item["expires_at"] = None
                item["days_remaining"] = None
                item["renewable"] = False

    def provision_phones(self, count: int = 1, user_id: int = None) -> List[CloudPhonePool]:
        """消耗订阅额度开通云手机实例（带行锁，防并发超开）。"""
        if user_id is None:
            raise ValueError("user_id is required")
        if count < 1:
            return []

        try:
            self.db.query(CloudPhoneSubscription).filter(
                CloudPhoneSubscription.user_id == user_id,
                CloudPhoneSubscription.status == "active",
            ).with_for_update().all()
            self.db.query(CloudPhonePool).filter(
                CloudPhonePool.created_by == user_id,
            ).with_for_update().all()

            self._assert_provision_allowed(user_id, count)
        except (CloudPhoneQuotaExceeded, CloudPhoneProvisionRateLimited):
            self.db.rollback()
            raise

        phones = self._auto_scale(count, user_id)
        if not phones:
            raise CloudPhoneQuotaExceeded("云手机开通失败，请稍后重试")
        if len(phones) < count:
            raise CloudPhoneQuotaExceeded(
                f"仅成功开通 {len(phones)}/{count} 台，请稍后重试"
            )

        self._bind_subscriptions_to_phones(user_id, phones)
        return phones

    def manual_scale(self, count: int = 1, user_id: int = None) -> List[CloudPhonePool]:
        """开通云手机（消耗订阅额度，不再扣积分）。"""
        return self.provision_phones(count, user_id)
    
    def ensure_pool_size(self, min_size: int = None) -> int:
        """确保资源池最小大小"""
        min_size = min_size or self.MIN_AVAILABLE_POOL
        current = self.get_available_count()
        
        if current < min_size:
            needed = min_size - current
            return len(self._auto_scale(needed))
        
        return 0
