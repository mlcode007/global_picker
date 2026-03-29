from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.core.security import get_current_user
from app.schemas.common import PagedResponse, Response
from app.schemas.product import ProductCreate, ProductUpdate, ProductOut, ProductBatchImport
from app.services import product_service
from app.workers.tiktok_crawler import run_crawl_task

router = APIRouter(prefix="/products", tags=["商品管理"])


@router.post("", response_model=Response[ProductOut], summary="新增商品")
async def add_product(
    data: ProductCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product, task = product_service.create_product(db, data, current_user.id)
    if task:
        background_tasks.add_task(run_crawl_task, task.id)
        return Response(data=ProductOut.model_validate(product))
    if product and not task:
        # task 为 None 可能是重复链接或者已共享采集数据
        existing = product_service.get_product(db, product.id, current_user.id)
        if existing and existing.crawl_task_id:
            return Response(data=ProductOut.model_validate(product))
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=409,
        content={"code": 409, "message": "该链接已存在", "data": None},
    )


@router.post("/batch", summary="批量导入商品链接")
async def batch_import(
    data: ProductBatchImport,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = product_service.batch_create_products(db, data.urls, current_user.id)
    for task_id in result.get("task_ids", []):
        background_tasks.add_task(run_crawl_task, task_id)
    return Response(data=result)


@router.get("", response_model=Response[PagedResponse[ProductOut]], summary="商品列表")
def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="pending/selected/abandoned"),
    region: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    order_by: str = Query("created_at"),
    order_dir: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    total, items = product_service.get_products(
        db, current_user.id, page, page_size, status, region, keyword, order_by, order_dir
    )
    return Response(
        data=PagedResponse(
            total=total,
            page=page,
            page_size=page_size,
            items=[ProductOut.model_validate(p) for p in items],
        )
    )


@router.get("/{product_id}", response_model=Response[ProductOut], summary="商品详情")
def get_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = product_service.get_product(db, product_id, current_user.id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return Response(data=ProductOut.model_validate(product))


@router.patch("/{product_id}", response_model=Response[ProductOut], summary="更新商品状态/备注")
def update_product(
    product_id: int,
    data: ProductUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = product_service.update_product(db, product_id, data, current_user.id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return Response(data=ProductOut.model_validate(product))


@router.delete("/{product_id}", summary="删除商品（软删除）")
def delete_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ok = product_service.delete_product(db, product_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="商品不存在")
    return Response(message="删除成功")
