from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services import product_service
from app.core.security import get_current_user
from app.schemas.common import PagedResponse, Response
from app.schemas.product import ProductCreate, ProductUpdate, ProductOut, ProductBatchImport, ProductBatchDelete
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
        content={"code": 409, "message": "该商品已存在（同一 TikTok 商品 ID）", "data": None},
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


@router.post("/batch-delete", summary="批量删除商品（软删除）")
def batch_delete_products_post(
    data: ProductBatchDelete,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """使用 JSON 传 ID，避免 DELETE + Query 与 /{product_id} 路由冲突及 URL 过长。"""
    count = product_service.batch_delete_products(db, data.product_ids, current_user.id)
    return Response(data={"deleted_count": count}, message=f"成功删除 {count} 个商品")


@router.get("", response_model=Response[PagedResponse[ProductOut]], summary="商品列表")
def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    status: Optional[str] = Query(None, description="pending/selected/abandoned/erp_synced"),
    region: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    price_cny_min: Optional[float] = Query(None, description="TikTok人民币价格下限"),
    price_cny_max: Optional[float] = Query(None, description="TikTok人民币价格上限"),
    profit_min: Optional[float] = Query(None, description="预估利润下限"),
    profit_max: Optional[float] = Query(None, description="预估利润上限"),
    profit_rate_min: Optional[float] = Query(None, description="预估利润率下限(小数,例如0.2表示20%)"),
    profit_rate_max: Optional[float] = Query(None, description="预估利润率上限(小数,例如0.2表示20%)"),
    pdd_matched: Optional[bool] = Query(None, description="是否已匹配拼多多(True=已匹配/False=未匹配)"),
    created_at_start: Optional[str] = Query(None, description="导入时间起始(ISO格式,如2026-01-01)"),
    created_at_end: Optional[str] = Query(None, description="导入时间截止(ISO格式,如2026-12-31)"),
    order_by: str = Query("created_at"),
    order_dir: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    total, items = product_service.get_products(
        db, current_user.id, page, page_size, status, region, keyword,
        order_by, order_dir,
        price_cny_min=price_cny_min, price_cny_max=price_cny_max,
        profit_min=profit_min, profit_max=profit_max,
        profit_rate_min=profit_rate_min, profit_rate_max=profit_rate_max,
        pdd_matched=pdd_matched,
        created_at_start=created_at_start, created_at_end=created_at_end,
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


@router.delete("/batch", summary="批量删除商品（软删除，Query 传参，已弃用请用 POST /batch-delete）")
def batch_delete_products_query(
    product_ids: str = Query(..., description="商品ID列表，逗号分隔"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ids = [int(i.strip()) for i in product_ids.split(",") if i.strip().isdigit()]
    if not ids:
        raise HTTPException(status_code=400, detail="请选择要删除的商品")
    count = product_service.batch_delete_products(db, ids, current_user.id)
    return Response(data={"deleted_count": count}, message=f"成功删除 {count} 个商品")


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
