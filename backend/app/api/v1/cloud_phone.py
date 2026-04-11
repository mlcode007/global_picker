"""
云手机管理 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.cloud_phone import CloudPhonePool, UserCloudPhone
from app.models.user import User
from app.services.cloud_phone_service import CloudPhoneManager
from app.core.security import get_current_user

router = APIRouter(tags=["cloud-phone"])


@router.get("/cloud-phone/pool/stats")
async def get_pool_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取云手机池统计信息"""
    manager = CloudPhoneManager(db)
    stats = manager.get_pool_stats()
    return {
        "code": 0,
        "msg": "success",
        "data": stats
    }


@router.get("/cloud-phone/pool/list")
async def list_pool(
    status: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = 1,
    page_size: int = 10
):
    """获取云手机池列表"""
    query = db.query(CloudPhonePool)
    # 只返回当前用户创建的云手机
    query = query.filter(CloudPhonePool.created_by == current_user.id)
    if status:
        query = query.filter(CloudPhonePool.status == status)
    
    total = query.count()
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()
    
    return {
        "code": 0,
        "msg": "success",
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    }


@router.post("/cloud-phone/pool/scale")
async def manual_scale(
    count: int = 1,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """手动扩容云手机"""
    manager = CloudPhoneManager(db)
    new_phones = manager.manual_scale(count, current_user.id)
    return {
        "code": 0,
        "msg": f"成功扩容 {len(new_phones)} 台云手机",
        "data": [p.phone_id for p in new_phones]
    }


@router.post("/cloud-phone/acquire")
async def acquire_phone(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """为当前用户分配云手机"""
    manager = CloudPhoneManager(db)
    
    # 检查用户是否已有云手机
    existing = manager.get_user_phone(current_user.id)
    if existing:
        return {
            "code": -2,
            "msg": "您已经绑定了云手机，无法再次获取",
            "data": None
        }
    
    binding = manager.acquire_phone_for_user(current_user.id)
    
    if binding:
        return {
            "code": 0,
            "msg": "云手机分配成功",
            "data": {
                "phone_id": binding.phone_id,
                "bind_at": binding.bind_at.isoformat()
            }
        }
    else:
        return {
            "code": -1,
            "msg": "云手机资源紧张，请稍后再试",
            "data": None
        }


@router.post("/cloud-phone/release")
async def release_phone(
    force: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """释放当前用户的云手机"""
    manager = CloudPhoneManager(db)
    success = manager.unbind_from_user(current_user.id, force=force)
    
    if success:
        return {
            "code": 0,
            "msg": "云手机已释放",
            "data": None
        }
    else:
        return {
            "code": -1,
            "msg": "用户没有绑定云手机",
            "data": None
        }


@router.get("/cloud-phone/my-phone")
async def get_my_phone(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户的云手机信息"""
    manager = CloudPhoneManager(db)
    binding = manager.get_user_phone(current_user.id)
    
    if binding:
        return {
            "code": 0,
            "msg": "success",
            "data": {
                "phone_id": binding.phone_id,
                "bind_at": binding.bind_at.isoformat(),
                "is_active": binding.is_active
            }
        }
    else:
        return {
            "code": -1,
            "msg": "用户未绑定云手机",
            "data": None
        }


@router.post("/cloud-phone/recover")
async def recover_offline_phones(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """恢复离线云手机"""
    manager = CloudPhoneManager(db)
    recovered = manager.recover_offline_phones()
    
    return {
        "code": 0,
        "msg": f"成功恢复 {recovered} 台云手机",
        "data": {"recovered": recovered}
    }


@router.get("/cloud-phone/health")
async def check_phone_health(
    phone_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """检查云手机健康状态"""
    manager = CloudPhoneManager(db)
    is_healthy = manager.check_phone_health(phone_id)
    
    return {
        "code": 0,
        "data": {
            "phone_id": phone_id,
            "is_healthy": is_healthy
        }
    }
