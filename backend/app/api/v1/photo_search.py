"""
拍照购 API 路由
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.common import Response
from app.schemas.photo_search import (
    PhotoSearchTaskCreate,
    PhotoSearchTaskOut,
    DeviceOut,
    DeviceActionLogOut,
)
from app.services import photo_search_service, product_service
from app.services.photo_search_service import DuplicateTaskError
from app.models.device import Device

router = APIRouter(prefix="/pdd/photo-search", tags=["拼多多拍照购"])


@router.post("/tasks", response_model=Response[PhotoSearchTaskOut], summary="创建拍照购任务")
def create_task(
    data: PhotoSearchTaskCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product_service.get_product(db, data.product_id, current_user.id)
    try:
        task = photo_search_service.create_task(
            db,
            data.product_id,
            data.image_index,
            fetch_pdd_links=data.fetch_pdd_links,
            max_candidates=data.max_candidates,
        )
    except DuplicateTaskError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    from app.workers.pdd_photo.worker import execute_photo_search_task
    background_tasks.add_task(execute_photo_search_task, task.id)

    return Response(data=PhotoSearchTaskOut.model_validate(task))


@router.get("/tasks/{task_id}", response_model=Response[PhotoSearchTaskOut], summary="查询任务状态")
def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = photo_search_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return Response(data=PhotoSearchTaskOut.model_validate(task))


@router.get(
    "/tasks/product/{product_id}",
    response_model=Response[List[PhotoSearchTaskOut]],
    summary="查询商品的拍照购任务历史",
)
def get_tasks_by_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product_service.get_product(db, product_id, current_user.id)
    tasks = photo_search_service.get_tasks_by_product(db, product_id)
    return Response(data=[PhotoSearchTaskOut.model_validate(t) for t in tasks])


@router.post("/tasks/{task_id}/retry", response_model=Response[PhotoSearchTaskOut], summary="重试任务")
def retry_task(
    task_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        task = photo_search_service.retry_task(db, task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    from app.workers.pdd_photo.worker import execute_photo_search_task
    background_tasks.add_task(execute_photo_search_task, task.id)

    return Response(data=PhotoSearchTaskOut.model_validate(task))


@router.post("/tasks/{task_id}/cancel", summary="取消任务")
def cancel_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        photo_search_service.cancel_task(db, task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return Response(message="任务已取消")


@router.get(
    "/tasks/{task_id}/logs",
    response_model=Response[List[DeviceActionLogOut]],
    summary="查询任务执行日志",
)
def get_task_logs(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logs = photo_search_service.get_action_logs(db, task_id)
    return Response(data=[DeviceActionLogOut.model_validate(l) for l in logs])


@router.post(
    "/tasks/{task_id}/sync-images",
    response_model=Response[dict],
    summary="将任务结果中的图片 URL 同步到 pdd_matches",
)
def sync_task_images_to_matches(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """从 raw_result_json.candidates[].image_url 写回数据库（如 OSS 链接）。"""
    try:
        result = photo_search_service.sync_match_images_from_task_result(db, task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return Response(
        data=result,
        message=f"已更新 {result['updated']} 条匹配记录（图片 / 商品链接）",
    )


@router.get("/devices", response_model=Response[List[DeviceOut]], summary="查询设备池")
def list_devices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    devices = db.query(Device).all()
    return Response(data=[DeviceOut.model_validate(d) for d in devices])


@router.post("/devices/{device_id}/heartbeat", summary="设备心跳检测")
def device_heartbeat(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.workers.pdd_photo.device_manager import DeviceManager
    mgr = DeviceManager(db)
    ok = mgr.heartbeat(device_id)
    return Response(data={"connected": ok})
