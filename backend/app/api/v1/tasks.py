from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.crawl_task import CrawlTask
from app.models.product import Product
from app.schemas.common import Response
from app.schemas.crawl_task import CrawlTaskOut
from app.schemas.product import ProductOut
from app.workers.tiktok_crawler_v2 import run_crawl_task, CRAWL_CONCURRENCY_LIMIT

router = APIRouter(prefix="/tasks", tags=["抓取任务"])


class BatchRetryRequest(BaseModel):
    task_ids: List[int]


@router.get("", response_model=Response[List[CrawlTaskOut]], summary="批量查询任务状态")
def query_tasks(
    ids: str = Query(..., description="逗号分隔的任务ID，如 1,2,3"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    id_list = [int(i.strip()) for i in ids.split(",") if i.strip().isdigit()]
    if not id_list:
        return Response(data=[])
    tasks = db.query(CrawlTask).filter(CrawlTask.id.in_(id_list)).all()
    return Response(data=[CrawlTaskOut.model_validate(t) for t in tasks])


@router.get("/{task_id}", response_model=Response[CrawlTaskOut], summary="查询单个任务状态")
def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.query(CrawlTask).filter(CrawlTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    base = CrawlTaskOut.model_validate(task)
    if task.status == "done":
        p = (
            db.query(Product)
            .filter(
                Product.crawl_task_id == task_id,
                Product.user_id == current_user.id,
                Product.is_deleted == 0,
            )
            .first()
        )
        if p:
            base = base.model_copy(update={"product": ProductOut.model_validate(p)})
    return Response(data=base)


@router.post("/{task_id}/retry", summary="重新采集（支持 failed / done 状态）")
def retry_task(
    task_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.query(CrawlTask).filter(CrawlTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status == "running":
        raise HTTPException(status_code=400, detail="任务正在采集中，请稍后")
    task.status = "pending"
    task.error_msg = None
    db.commit()
    db.refresh(task)
    background_tasks.add_task(run_crawl_task, task_id)
    return Response(data=CrawlTaskOut.model_validate(task))


@router.post("/batch-retry", summary="批量重新采集")
def batch_retry_tasks(
    data: BatchRetryRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tasks = db.query(CrawlTask).filter(
        CrawlTask.id.in_(data.task_ids),
        CrawlTask.status != "running",
    ).all()

    found_ids = {t.id for t in tasks}
    results = []

    for task in tasks:
        task.status = "pending"
        task.error_msg = None
        task.status_detail = "排队等待中..."
        background_tasks.add_task(run_crawl_task, task.id)
        results.append({
            "task_id": task.id,
            "status": "pending",
            "message": "已加入队列",
        })

    db.commit()

    skipped_ids = set(data.task_ids) - found_ids
    for tid in skipped_ids:
        results.append({
            "task_id": tid,
            "status": "skipped",
            "message": "任务正在运行或不存在",
        })

    return Response(data={
        "submitted": len(results) - len(skipped_ids),
        "skipped": len(skipped_ids),
        "concurrency_limit": CRAWL_CONCURRENCY_LIMIT,
        "results": results,
    })
