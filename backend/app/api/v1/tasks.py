from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.crawl_task import CrawlTask
from app.schemas.common import Response
from app.schemas.crawl_task import CrawlTaskOut
from app.workers.tiktok_crawler import run_crawl_task

router = APIRouter(prefix="/tasks", tags=["抓取任务"])


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
    return Response(data=CrawlTaskOut.model_validate(task))


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
