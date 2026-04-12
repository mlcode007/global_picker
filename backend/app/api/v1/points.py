"""
积分管理 API
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.user import User
from app.services.points_service import PointsManager
from app.core.security import get_current_user

router = APIRouter(tags=["points"])


@router.get("/points")
async def get_points(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户积分信息"""
    manager = PointsManager(db)
    user_points = manager.get_user_points(current_user.id)
    return {
        "code": 0,
        "msg": "success",
        "data": {
            "points": user_points.points,
            "total_earned": user_points.total_earned,
            "total_consumed": user_points.total_consumed
        }
    }


@router.get("/points/transactions")
async def get_points_transactions(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户积分交易记录"""
    manager = PointsManager(db)
    transactions = manager.get_transactions(current_user.id, limit, offset)
    
    transaction_list = []
    for tx in transactions:
        transaction_list.append({
            "id": tx.id,
            "type": tx.type,
            "amount": tx.amount,
            "reason": tx.reason,
            "related_id": tx.related_id,
            "created_at": tx.created_at.isoformat()
        })
    
    return {
        "code": 0,
        "msg": "success",
        "data": transaction_list
    }


@router.post("/points/check")
async def check_points(
    request_data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """检查用户积分是否足够"""
    amount = request_data.get("amount")
    if amount is None:
        return {
            "code": -1,
            "msg": "缺少参数 amount",
            "data": None
        }
    
    manager = PointsManager(db)
    is_enough = manager.check_points(current_user.id, amount)
    
    return {
        "code": 0,
        "msg": "success",
        "data": {
            "is_enough": is_enough,
            "required": amount,
            "available": manager.get_user_points(current_user.id).points
        }
    }


@router.post("/points/recharge")
async def recharge_points(
    request_data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """积分充值"""
    amount = request_data.get("amount")
    if amount is None:
        return {
            "code": -1,
            "msg": "缺少参数 amount",
            "data": None
        }
    
    if amount <= 0:
        return {
            "code": -1,
            "msg": "充值金额必须大于0",
            "data": None
        }
    
    manager = PointsManager(db)
    success = manager.add_points(current_user.id, amount, "积分充值")
    
    if success:
        return {
            "code": 0,
            "msg": "充值成功",
            "data": {
                "points": manager.get_user_points(current_user.id).points
            }
        }
    else:
        return {
            "code": -1,
            "msg": "充值失败",
            "data": None
        }
