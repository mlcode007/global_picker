"""
云手机管理器
- 云手机池管理
- 用户绑定管理
- 资源分配与回收
- 自动扩容机制
"""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from app.models.cloud_phone import CloudPhonePool, UserCloudPhone
from app.models.user import User
from app.util.chinac.chinac_open_api import ChinacOpenApi
from app.util.chinac_utils import cloud_phone_create

logger = logging.getLogger(__name__)


class CloudPhoneManager:
    """云手机管理器 - 负责云手机资源的全生命周期管理"""
    
    # 阈值配置
    MIN_AVAILABLE_POOL = 3  # 最小可用池数量
    MAX_AUTO_SCALE = 10     # 最大自动扩容数量
    AUTO_SCALE_THRESHOLD = 0.3  # 自动扩容触发阈值（可用率低于30%）
    
    def __init__(self, db: Session):
        self.db = db
        self.api = ChinacOpenApi()
    
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
    
    def remove_from_pool(self, phone_id: str) -> bool:
        """从资源池移除云手机（永久删除）"""
        phone = self.db.query(CloudPhonePool).filter(CloudPhonePool.phone_id == phone_id).first()
        if phone:
            self.db.delete(phone)
            self.db.commit()
            logger.info("Cloud phone %s removed from pool", phone_id)
            return True
        return False
    
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
        return self.db.query(CloudPhonePool).filter(
            CloudPhonePool.status == "available"
        ).count()
    
    def list_available_phones(self, limit: int = 10) -> List[CloudPhonePool]:
        """获取可用云手机列表"""
        return self.db.query(CloudPhonePool).filter(
            CloudPhonePool.status == "available"
        ).limit(limit).all()
    
    def list_all_phones(self) -> List[CloudPhonePool]:
        """获取所有云手机"""
        return self.db.query(CloudPhonePool).all()
    
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
        phone = self.db.query(CloudPhonePool).filter(
            CloudPhonePool.phone_id == phone_id
        ).first()
        
        if not phone:
            logger.error("Cloud phone %s not found in pool", phone_id)
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
        2. 从资源池分配空闲云手机
        3. 触发自动扩容（如果需要）
        """
        # 检查用户是否已有云手机
        existing = self.get_user_phone(user_id)
        if existing:
            logger.warning("User %d already has cloud phone: %s, cannot acquire another one", user_id, existing.phone_id)
            return None
        
        # 从资源池分配
        available = self._try_acquire_from_pool()
        if available:
            return self.bind_to_user(user_id, available.phone_id)
        
        # 触发自动扩容
        if self._should_auto_scale():
            new_phones = self._auto_scale(1)  # 只创建1台
            if new_phones:
                # 等待云手机状态就绪
                time.sleep(2)  # 短暂延迟，确保云手机状态更新
                return self.bind_to_user(user_id, new_phones[0].phone_id)
        
        logger.warning("No available cloud phone for user %d", user_id)
        return None
    
    def _try_acquire_from_pool(self) -> Optional[CloudPhonePool]:
        """尝试从资源池获取可用云手机"""
        phone = self.db.query(CloudPhonePool).filter(
            CloudPhonePool.status == "available"
        ).with_for_update(skip_locked=True).first()
        
        if phone:
            phone.status = "binding"
            phone.updated_at = datetime.now()
            self.db.commit()
        
        return phone
    
    def _should_auto_scale(self) -> bool:
        """判断是否需要自动扩容"""
        total = self.db.query(CloudPhonePool).count()
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
        
        # 安全检查：防止频繁调用
        if hasattr(self, '_last_scale_time'):
            time_since_last = time.time() - self._last_scale_time
            if time_since_last < 60:  # 限制1分钟内只能调用一次
                logger.warning("Scale rate limit exceeded: %s seconds", time_since_last)
                return []
        
        self._last_scale_time = time.time()
        
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
                phone = self.add_to_pool(
                    phone_id=phone_id,
                    phone_name=phone_name,
                    instance_type="ci.g5.large",
                    created_by=user_id
                )
                
                # 如果提供了用户ID，直接绑定到该用户
                if user_id:
                    binding = self.bind_to_user(user_id, phone_id)
                    if binding:
                        logger.info("Cloud phone %s bound to user %d", phone_id, user_id)
                    else:
                        logger.warning("Failed to bind cloud phone %s to user %d", phone_id, user_id)
                
                created.append(phone)
                logger.info("Successfully created cloud phone: %s", phone_id)
                
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
            data = self.api.do_describe_cloud_phones(phone_ids=[phone_id])
            
            if data and 'CloudPhoneSet' in data:
                phone_status = data['CloudPhoneSet'][0].get('Status', '')
                return phone_status in ['RUNNING', 'STARTING']
            
            return False
            
        except Exception as e:
            logger.error("Failed to check cloud phone %s health: %s", phone_id, str(e))
            return False
    
    def recover_offline_phones(self) -> int:
        """恢复离线云手机"""
        offline_phones = self.db.query(CloudPhonePool).filter(
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
        total = self.db.query(CloudPhonePool).count()
        available = self.get_available_count()
        bound = self.db.query(CloudPhonePool).filter(
            CloudPhonePool.status == "bound"
        ).count()
        offline = self.db.query(CloudPhonePool).filter(
            CloudPhonePool.status == "offline"
        ).count()
        maintenance = self.db.query(CloudPhonePool).filter(
            CloudPhonePool.status == "maintenance"
        ).count()
        
        return {
            "total": total,
            "available": available,
            "bound": bound,
            "offline": offline,
            "maintenance": maintenance,
            "available_rate": available / total if total > 0 else 0
        }
    
    # ── 扩容接口（供外部调用）──────────────────────────────────────
    
    def manual_scale(self, count: int = 1, user_id: int = None) -> List[CloudPhonePool]:
        """手动扩容云手机"""
        return self._auto_scale(count, user_id)
    
    def ensure_pool_size(self, min_size: int = None) -> int:
        """确保资源池最小大小"""
        min_size = min_size or self.MIN_AVAILABLE_POOL
        current = self.get_available_count()
        
        if current < min_size:
            needed = min_size - current
            return len(self._auto_scale(needed))
        
        return 0
