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
    BatchPhotoSearchTaskCreate,
    BatchTaskResult,
    BatchTaskStatusOut,
    TaskQueueStatus,
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


# ── 批量任务接口 ──────────────────────────────────────────────────
@router.post("/tasks/batch", response_model=Response[BatchTaskResult], summary="批量创建拍照购任务")
def create_batch_tasks(
    data: BatchPhotoSearchTaskCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    批量为多个商品创建拍照购任务，支持并行执行。
    
    当有N台云手机时，会自动并行处理N个商品的拍照购任务。
    """
    if not data.product_ids:
        raise HTTPException(status_code=400, detail="商品ID列表不能为空")

    for product_id in data.product_ids:
        product_service.get_product(db, product_id, current_user.id)

    result = photo_search_service.create_batch_tasks(
        db,
        data.product_ids,
        current_user.id,
        image_index=data.image_index,
        fetch_pdd_links=data.fetch_pdd_links,
        max_candidates=data.max_candidates,
    )

    # 设置并发度（如果指定）
    if data.concurrency is not None:
        from app.workers.pdd_photo.task_scheduler import set_scheduler_concurrency
        set_scheduler_concurrency(data.concurrency)

    # 调度任务执行
    if result['task_ids']:
        from app.workers.pdd_photo.task_scheduler import schedule_tasks
        background_tasks.add_task(schedule_tasks, result['task_ids'])

    return Response(
        data=BatchTaskResult(**result),
        message=f"批量任务创建完成：成功 {result['created_count']} 个，跳过 {result['skipped_count']} 个，失败 {result['failed_count']} 个",
    )


@router.get("/tasks/batch/{batch_id}", response_model=Response[BatchTaskStatusOut], summary="查询批量任务状态")
def get_batch_task_status(
    batch_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = photo_search_service.get_batch_task_status(db, batch_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return Response(data=BatchTaskStatusOut(**result))


# ── 队列管理接口 ──────────────────────────────────────────────────


@router.get("/queue/status", response_model=Response[TaskQueueStatus], summary="获取任务队列状态")
def get_queue_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前任务队列状态，包括等待中、运行中、成功、失败的任务数量，以及设备状态。"""
    result = photo_search_service.get_task_queue_status(db)
    return Response(data=TaskQueueStatus(**result))


@router.post("/queue/schedule", summary="调度等待中的任务")
def schedule_queued_tasks(
    limit: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """将数据库中 queued 状态的任务加入调度队列，等待可用设备执行。"""
    count = photo_search_service.schedule_queued_tasks(db, limit)
    return Response(
        data={"scheduled_count": count},
        message=f"已调度 {count} 个任务",
    )


@router.post("/queue/concurrency", summary="设置队列并发度")
def set_queue_concurrency(
    max_concurrent: int = None,
    current_user: User = Depends(get_current_user),
):
    """
    设置最大并发任务数。
    
    - max_concurrent: 最大并发数，为 None 时使用所有可用设备
    - 当有2台云手机时，设置为2即可实现两个商品并行跑拍照购
    """
    from app.workers.pdd_photo.task_scheduler import set_scheduler_concurrency
    set_scheduler_concurrency(max_concurrent)
    return Response(
        message=f"并发度已设置为 {'全部设备' if max_concurrent is None else max_concurrent}",
    )
