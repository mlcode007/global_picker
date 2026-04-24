from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.core.security import get_current_user
from app.schemas.common import Response
from app.services.quota_service import QuotaManager

router = APIRouter(prefix="/quota", tags=["配额管理"])


class QuotaRecordRequest(BaseModel):
    product_url: Optional[str] = None
    product_id: Optional[int] = None


@router.get("/status", response_model=Response, summary="获取今日配额状态")
def get_quota_status(current_user: User = Depends(get_current_user), db=Depends(get_db)):
    """获取用户今日采集配额使用情况"""
    quota_manager = QuotaManager(db)
    status = quota_manager.get_quota_status(current_user.id)
    return Response(data=status)


@router.post("/record", response_model=Response, summary="记录采集操作")
def record_collection(
    data: QuotaRecordRequest = None,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """记录一次采集操作，并返回最新配额状态"""
    quota_manager = QuotaManager(db)

    if not quota_manager.check_quota(current_user.id):
        status = quota_manager.get_quota_status(current_user.id)
        raise HTTPException(
            status_code=403,
            detail={
                "code": "QUOTA_EXCEEDED",
                "message": f"今日采集配额已用完（{status['today_count']}/{status['daily_limit']}）",
            },
        )

    result = quota_manager.record_collection(
        user_id=current_user.id,
        product_url=data.product_url if data else None,
        product_id=data.product_id if data else None,
    )

    if not result["success"]:
        raise HTTPException(status_code=403, detail=result["error"])

    return Response(data=result["data"])
