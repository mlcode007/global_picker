from decimal import Decimal
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.product import Product
from app.models.crawl_task import CrawlTask
from app.schemas.product import ProductCreate, ProductUpdate


def _copy_crawl_data(source: Product, target: Product) -> None:
    """从已采集的商品复制数据到新商品（共享采集结果，减少重复抓取）"""
    fields = [
        "tiktok_product_id", "title", "description", "price", "currency",
        "price_cny", "sales_volume", "rating", "review_count", "stock_status",
        "region", "shop_name", "shop_id", "original_price", "discount",
        "seller_location", "shipping_fee", "free_shipping",
        "delivery_days_min", "delivery_days_max",
        "main_image_url", "image_urls", "category",
    ]
    for f in fields:
        val = getattr(source, f, None)
        if val is not None:
            setattr(target, f, val)


def _find_shared_product(db: Session, tiktok_url: str, exclude_user_id: int) -> Optional[Product]:
    """查找其他用户已成功采集的同一商品，用于共享数据"""
    return (
        db.query(Product)
        .join(CrawlTask, Product.crawl_task_id == CrawlTask.id)
        .filter(
            Product.tiktok_url == tiktok_url,
            Product.is_deleted == 0,
            Product.user_id != exclude_user_id,
            CrawlTask.status == "done",
        )
        .first()
    )


def create_product(db: Session, data: ProductCreate, user_id: int) -> Tuple[Product, Optional[CrawlTask]]:
    """新增商品并创建抓取任务，支持共享采集数据"""
    existing = db.query(Product).filter(
        Product.tiktok_url == data.tiktok_url,
        Product.user_id == user_id,
        Product.is_deleted == 0,
    ).first()
    if existing:
        return existing, None

    # 检查是否有其他用户已采集成功的同一商品
    shared = _find_shared_product(db, data.tiktok_url, user_id)

    task = CrawlTask(url=data.tiktok_url, status="pending" if not shared else "done")
    db.add(task)
    db.flush()

    # 软删除记录恢复
    deleted = db.query(Product).filter(
        Product.tiktok_url == data.tiktok_url,
        Product.user_id == user_id,
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
        if shared:
            _copy_crawl_data(shared, deleted)
            deleted.status = "pending"
        db.commit()
        db.refresh(deleted)
        return deleted, task if not shared else None

    product = Product(
        user_id=user_id,
        crawl_task_id=task.id,
        tiktok_url=data.tiktok_url,
        title=data.title or "",
        price=data.price or Decimal("0"),
        currency=data.currency,
        sales_volume=data.sales_volume or 0,
        region=data.region,
        remark=data.remark,
    )

    if shared:
        _copy_crawl_data(shared, product)

    db.add(product)
    db.commit()
    db.refresh(product)
    return product, task if not shared else None


def batch_create_products(db: Session, urls: List[str], user_id: int) -> dict:
    """批量导入商品链接，支持共享采集结果"""
    created, duplicates, task_ids = [], [], []
    for url in urls:
        url = url.strip()
        if not url:
            continue

        existing = db.query(Product).filter(
            Product.tiktok_url == url,
            Product.user_id == user_id,
            Product.is_deleted == 0,
        ).first()
        if existing:
            duplicates.append(url)
            continue

        shared = _find_shared_product(db, url, user_id)

        # 已存在但软删除 → 恢复记录
        deleted = db.query(Product).filter(
            Product.tiktok_url == url,
            Product.user_id == user_id,
            Product.is_deleted == 1,
        ).first()
        if deleted:
            task = CrawlTask(url=url, status="done" if shared else "pending")
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
            if shared:
                _copy_crawl_data(shared, deleted)
            else:
                task_ids.append(task.id)
            created.append(url)
            continue

        task = CrawlTask(url=url, status="done" if shared else "pending")
        db.add(task)
        db.flush()
        product = Product(user_id=user_id, crawl_task_id=task.id, tiktok_url=url)
        if shared:
            _copy_crawl_data(shared, product)
        else:
            task_ids.append(task.id)
        db.add(product)
        created.append(url)

    db.commit()
    return {"created": len(created), "duplicates": len(duplicates), "task_ids": task_ids}


def get_products(
    db: Session,
    user_id: int,
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    region: Optional[str] = None,
    keyword: Optional[str] = None,
    order_by: str = "created_at",
    order_dir: str = "desc",
    price_cny_min: Optional[float] = None,
    price_cny_max: Optional[float] = None,
    profit_min: Optional[float] = None,
    profit_max: Optional[float] = None,
) -> Tuple[int, List[Product]]:
    """商品列表（按用户隔离，分页、过滤、排序）"""
    query = db.query(Product).filter(Product.is_deleted == 0, Product.user_id == user_id)

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
    if price_cny_min is not None:
        query = query.filter(Product.price_cny >= price_cny_min)
    if price_cny_max is not None:
        query = query.filter(Product.price_cny <= price_cny_max)
    if profit_min is not None:
        query = query.filter(Product.estimated_profit >= profit_min)
    if profit_max is not None:
        query = query.filter(Product.estimated_profit <= profit_max)

    total = query.count()

    sort_col = getattr(Product, order_by, Product.created_at)
    if order_dir == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return total, items


def get_product(db: Session, product_id: int, user_id: int = None) -> Optional[Product]:
    query = db.query(Product).filter(Product.id == product_id, Product.is_deleted == 0)
    if user_id is not None:
        query = query.filter(Product.user_id == user_id)
    return query.first()


def update_product(db: Session, product_id: int, data: ProductUpdate, user_id: int = None) -> Optional[Product]:
    product = get_product(db, product_id, user_id)
    if not product:
        return None
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product_id: int, user_id: int = None) -> bool:
    product = get_product(db, product_id, user_id)
    if not product:
        return False
    product.is_deleted = 1
    db.commit()
    return True
