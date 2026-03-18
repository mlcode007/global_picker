from decimal import Decimal
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.product import Product
from app.models.crawl_task import CrawlTask
from app.schemas.product import ProductCreate, ProductUpdate


def create_product(db: Session, data: ProductCreate) -> Tuple[Product, CrawlTask]:
    """新增商品并创建抓取任务"""
    # 已存在且未删除 → 重复
    existing = db.query(Product).filter(
        Product.tiktok_url == data.tiktok_url,
        Product.is_deleted == 0,
    ).first()
    if existing:
        return existing, None

    task = CrawlTask(url=data.tiktok_url, status="pending")
    db.add(task)
    db.flush()

    # 软删除记录 → 恢复并重置
    deleted = db.query(Product).filter(
        Product.tiktok_url == data.tiktok_url,
        Product.is_deleted == 1,
    ).first()
    if deleted:
        deleted.is_deleted = 0
        deleted.status = "pending"
        deleted.crawl_task_id = task.id
        deleted.title = data.title or ""
        deleted.price = data.price or Decimal("0")
        deleted.currency = data.currency
        deleted.sales_volume = data.sales_volume or 0
        deleted.region = data.region
        deleted.remark = data.remark
        deleted.main_image_url = None
        deleted.image_urls = None
        db.commit()
        db.refresh(deleted)
        return deleted, task

    product = Product(
        crawl_task_id=task.id,
        tiktok_url=data.tiktok_url,
        title=data.title or "",
        price=data.price or Decimal("0"),
        currency=data.currency,
        sales_volume=data.sales_volume or 0,
        region=data.region,
        remark=data.remark,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product, task


def batch_create_products(db: Session, urls: List[str]) -> dict:
    """批量导入商品链接，返回新创建的 task_ids 供前端轮询进度"""
    created, duplicates, task_ids = [], [], []
    for url in urls:
        url = url.strip()
        if not url:
            continue

        # 已存在且未删除 → 视为重复跳过
        existing = db.query(Product).filter(
            Product.tiktok_url == url,
            Product.is_deleted == 0,
        ).first()
        if existing:
            duplicates.append(url)
            continue

        # 已存在但软删除 → 恢复记录并重新采集（避免唯一索引冲突）
        deleted = db.query(Product).filter(
            Product.tiktok_url == url,
            Product.is_deleted == 1,
        ).first()
        if deleted:
            task = CrawlTask(url=url, status="pending")
            db.add(task)
            db.flush()
            deleted.is_deleted = 0
            deleted.status = "pending"
            deleted.crawl_task_id = task.id
            deleted.title = ""
            deleted.price = Decimal("0")
            deleted.sales_volume = 0
            deleted.main_image_url = None
            deleted.image_urls = None
            created.append(url)
            task_ids.append(task.id)
            continue

        # 全新记录
        task = CrawlTask(url=url, status="pending")
        db.add(task)
        db.flush()
        product = Product(crawl_task_id=task.id, tiktok_url=url)
        db.add(product)
        created.append(url)
        task_ids.append(task.id)

    db.commit()
    return {"created": len(created), "duplicates": len(duplicates), "task_ids": task_ids}


def get_products(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    region: Optional[str] = None,
    keyword: Optional[str] = None,
    order_by: str = "created_at",
    order_dir: str = "desc",
) -> Tuple[int, List[Product]]:
    """商品列表（分页、过滤、排序）"""
    query = db.query(Product).filter(Product.is_deleted == 0)

    if status:
        query = query.filter(Product.status == status)
    if region:
        query = query.filter(Product.region == region)
    if keyword:
        query = query.filter(
            or_(
                Product.title.ilike(f"%{keyword}%"),
                Product.shop_name.ilike(f"%{keyword}%"),
            )
        )

    total = query.count()

    sort_col = getattr(Product, order_by, Product.created_at)
    if order_dir == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return total, items


def get_product(db: Session, product_id: int) -> Optional[Product]:
    return db.query(Product).filter(
        Product.id == product_id,
        Product.is_deleted == 0
    ).first()


def update_product(db: Session, product_id: int, data: ProductUpdate) -> Optional[Product]:
    product = get_product(db, product_id)
    if not product:
        return None
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product_id: int) -> bool:
    product = get_product(db, product_id)
    if not product:
        return False
    product.is_deleted = 1
    db.commit()
    return True
