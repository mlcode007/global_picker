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
    try:
        # 先检查数据库表结构
        from sqlalchemy import inspect, text
        inspector = inspect(CloudPhonePool)
        has_created_by = 'created_by' in [c.name for c in inspector.columns]
        
        # 构建查询条件
        where_clause = []
        params = {}
        
        # 添加 created_by 条件
        if has_created_by:
            where_clause.append("created_by = :user_id")
            params["user_id"] = current_user.id
        else:
            # 如果 created_by 字段不存在，返回空统计
            return {
                "code": 0,
                "msg": "success",
                "data": {
                    "total": 0,
                    "available": 0,
                    "bound": 0,
                    "offline": 0,
                    "maintenance": 0,
                    "available_rate": 0
                }
            }
        

        
        # 计算统计数据
        from sqlalchemy import text
        
        # 总数量
        if where_clause:
            total_sql = "SELECT COUNT(*) FROM cloud_phone_pool WHERE " + " AND ".join(where_clause)
            total = db.execute(text(total_sql), params).scalar() or 0
        else:
            total_sql = "SELECT COUNT(*) FROM cloud_phone_pool"
            total = db.execute(text(total_sql)).scalar() or 0
        
        # 可用数量
        if where_clause:
            available_sql = "SELECT COUNT(*) FROM cloud_phone_pool WHERE status = 'available' AND " + " AND ".join(where_clause)
            available = db.execute(text(available_sql), params).scalar() or 0
        else:
            available_sql = "SELECT COUNT(*) FROM cloud_phone_pool WHERE status = 'available'"
            available = db.execute(text(available_sql)).scalar() or 0
        
        # 已绑定数量
        if where_clause:
            bound_sql = "SELECT COUNT(*) FROM cloud_phone_pool WHERE status = 'bound' AND " + " AND ".join(where_clause)
            bound = db.execute(text(bound_sql), params).scalar() or 0
        else:
            bound_sql = "SELECT COUNT(*) FROM cloud_phone_pool WHERE status = 'bound'"
            bound = db.execute(text(bound_sql)).scalar() or 0
        
        # 离线数量（包括所有非可用状态）
        if where_clause:
            offline_sql = "SELECT COUNT(*) FROM cloud_phone_pool WHERE status IN ('offline', 'timeo', 'deleted', 'maintenance') AND " + " AND ".join(where_clause)
            offline = db.execute(text(offline_sql), params).scalar() or 0
        else:
            offline_sql = "SELECT COUNT(*) FROM cloud_phone_pool WHERE status IN ('offline', 'timeo', 'deleted', 'maintenance')"
            offline = db.execute(text(offline_sql)).scalar() or 0
        
        # 维护中数量
        if where_clause:
            maintenance_sql = "SELECT COUNT(*) FROM cloud_phone_pool WHERE status = 'maintenance' AND " + " AND ".join(where_clause)
            maintenance = db.execute(text(maintenance_sql), params).scalar() or 0
        else:
            maintenance_sql = "SELECT COUNT(*) FROM cloud_phone_pool WHERE status = 'maintenance'"
            maintenance = db.execute(text(maintenance_sql)).scalar() or 0
        
        # 构建统计结果
        stats = {
            "total": total,
            "available": available,
            "bound": bound,
            "offline": offline,
            "maintenance": maintenance,
            "available_rate": available / total if total > 0 else 0
        }
        
        return {
            "code": 0,
            "msg": "success",
            "data": stats
        }
    except Exception as e:
        import traceback
        print(f"Error in get_pool_stats: {e}")
        print(traceback.format_exc())
        return {
            "code": 0,
            "msg": "success",
            "data": {
                "total": 0,
                "available": 0,
                "bound": 0,
                "offline": 0,
                "maintenance": 0,
                "available_rate": 0
            }
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
    try:
        # 检查数据库表结构是否包含 created_by 字段
        from sqlalchemy import inspect
        inspector = inspect(CloudPhonePool)
        has_created_by = 'created_by' in [c.name for c in inspector.columns]
        
        # 使用原生 SQL 查询
        from sqlalchemy import text
        
        # 构建 WHERE 子句
        where_clause = []
        params = {}
        
        # 添加 created_by 条件
        if has_created_by:
            where_clause.append("created_by = :user_id")
            params["user_id"] = current_user.id
        
        # 添加 status 条件
        if status:
            where_clause.append("status = :status")
            params["status"] = status
        
        # 构建 WHERE 子句
        where_sql = " WHERE " + " AND ".join(where_clause) if where_clause else ""
        
        # 计算总数
        count_sql = f"SELECT COUNT(*) FROM cloud_phone_pool{where_sql}"
        total = db.execute(text(count_sql), params).scalar() or 0
        
        # 构建分页查询
        offset = (page - 1) * page_size
        select_sql = f"""
            SELECT 
                phone_id, phone_name, status, region, 
                instance_type, spec, created_at, updated_at
                {', created_by' if has_created_by else ''}
            FROM cloud_phone_pool
            {where_sql}
            ORDER BY 
                CASE 
                    WHEN status = 'available' THEN 0
                    ELSE 1
                END, 
                created_at DESC
            LIMIT :limit OFFSET :offset
        """
        params["limit"] = page_size
        params["offset"] = offset
        
        # 执行查询
        items = db.execute(text(select_sql), params).all()
        
        # 检查数据库表结构是否包含 adb_host_port 字段
        from sqlalchemy import inspect
        inspector = inspect(CloudPhonePool)
        has_adb_host_port = 'adb_host_port' in [c.name for c in inspector.columns]
        
        # 为每个云手机添加 adb_host_port 字段
        from app.util.chinac_utils import cloud_phone_describe_phone
        import json
        
        result_items = []
        for item in items:
            # 处理原生 SQL 查询结果（元组）
            if has_created_by:
                phone_id, phone_name, status, region, instance_type, spec, created_at, updated_at, created_by = item
            else:
                phone_id, phone_name, status, region, instance_type, spec, created_at, updated_at = item
            
            # 处理状态值，确保它在枚举中
            valid_statuses = ["available", "binding", "bound", "offline", "maintenance", "deleted", "adb_timeout"]
            if status == "timeo":
                # 将 timeo 转换为 adb_timeout
                status = "adb_timeout"
            elif status not in valid_statuses:
                # 如果状态值不在枚举中，将其转换为 offline
                status = "offline"
            
            # 构建返回数据
            item_data = {
                "phone_id": phone_id,
                "phone_name": phone_name,
                "status": status,
                "region": region,
                "instance_type": instance_type,
                "spec": spec,
                "created_at": created_at,
                "updated_at": updated_at,
                "created_by": created_by if has_created_by else None,
                "adb_host_port": None  # 默认值
            }
            
            # 优先从数据库中读取 adb_host_port 字段
            if has_adb_host_port:
                # 重新查询数据库，获取 adb_host_port 字段
                phone = db.query(CloudPhonePool).filter(CloudPhonePool.phone_id == item.phone_id).first()
                if phone and hasattr(phone, 'adb_host_port'):
                    item_data["adb_host_port"] = phone.adb_host_port
            
            # 如果数据库中没有 adb_host_port 字段，或者值为 None，再从云服务提供商的 API 获取
            if not item_data["adb_host_port"]:
                try:
                    # 获取云手机详细信息
                    device_info = cloud_phone_describe_phone(item.phone_id)
                    if 'data' in device_info and 'BasicInfo' in device_info['data']:
                        adb_host_port = device_info['data']['BasicInfo'].get('AdbHostPort')
                        item_data["adb_host_port"] = adb_host_port
                except Exception as e:
                    pass
            
            result_items.append(item_data)
        
        return {
            "code": 0,
            "msg": "success",
            "data": {
                "items": result_items,
                "total": total,
                "page": page,
                "page_size": page_size
            }
        }
    except Exception as e:
        import traceback
        print(f"Error in list_pool: {e}")
        print(traceback.format_exc())
        return {
            "code": 0,
            "msg": "success",
            "data": {
                "items": [],
                "total": 0,
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
            "msg": "获取云手机成功",
            "data": {
                "phone_id": binding.phone_id,
                "phone_name": binding.phone_name,
                "bind_at": binding.bind_at
            }
        }
    else:
        return {
            "code": -1,
            "msg": "获取云手机失败，可用设备不足",
            "data": None
        }


@router.delete("/cloud-phone/pool/remove/{phone_id}")
async def remove_phone(
    phone_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """从云手机池中删除设备"""
    manager = CloudPhoneManager(db)
    success = manager.remove_from_pool(phone_id)
    if success:
        return {
            "code": 0,
            "msg": "删除设备成功",
            "data": None
        }
    else:
        return {
            "code": -1,
            "msg": "设备不存在或删除失败",
            "data": None
        }


from pydantic import BaseModel

class ReleaseRequest(BaseModel):
    force: bool = False

@router.post("/cloud-phone/release")
async def release_phone(
    request: ReleaseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """释放当前用户的云手机"""
    manager = CloudPhoneManager(db)
    success = manager.unbind_from_user(current_user.id, force=request.force)
    
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


@router.get("/cloud-phone/live-url")
async def get_cloud_phone_live_url(
    phone_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取云手机远程操控/直播页 URL（供 Web SDK XingJieSdk.init 的 url 参数使用）。
    文档: https://www.chinac.com/docs/help/anc/content/open/WebSDK
    """
    if not phone_id or not phone_id.strip():
        return {
            "code": -1,
            "msg": "缺少 phone_id",
            "data": None,
        }

    from sqlalchemy import inspect

    inspector = inspect(CloudPhonePool)
    has_created_by = "created_by" in [c.name for c in inspector.columns]

    phone = db.query(CloudPhonePool).filter(CloudPhonePool.phone_id == phone_id).first()
    if not phone:
        return {
            "code": -1,
            "msg": "设备不存在",
            "data": None,
        }

    if has_created_by and phone.created_by is not None and phone.created_by != current_user.id:
        return {
            "code": -1,
            "msg": "无权访问该设备",
            "data": None,
        }

    try:
        from app.util.chinac_utils import cloud_phone_get_phone_pageUrl

        url = cloud_phone_get_phone_pageUrl(phone_id.strip())
        return {
            "code": 0,
            "msg": "success",
            "data": {"url": url, "phone_id": phone_id.strip()},
        }
    except Exception as e:
        import logging

        logging.getLogger(__name__).exception("get_cloud_phone_live_url failed: %s", e)
        return {
            "code": -1,
            "msg": f"获取直播地址失败: {e!s}",
            "data": None,
        }


@router.get("/cloud-phone/health")
async def check_phone_health(
    phone_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """检查云手机健康状态"""
    # 验证 phone_id 参数
    if not phone_id or "object PointerEvent" in phone_id:
        return {
            "code": -1,
            "message": "无效的设备ID",
            "data": None
        }
    
    manager = CloudPhoneManager(db)
    is_healthy = manager.check_phone_health(phone_id)
    
    # 获取设备的当前状态
    phone = db.query(CloudPhonePool).filter(CloudPhonePool.phone_id == phone_id).first()
    status = phone.status if phone else "unknown"
    
    return {
        "code": 0,
        "data": {
            "phone_id": phone_id,
            "is_healthy": is_healthy,
            "status": status
        }
    }
