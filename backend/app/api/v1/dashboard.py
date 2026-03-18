from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import func, case, and_, distinct
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import Response
from app.models import (
    Product, CrawlTask, PddMatch, ProfitRecord,
    Device, PhotoSearchTask,
)

router = APIRouter(prefix="/dashboard", tags=["看板"])


@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())

    # ── 商品统计 ──
    product_base = db.query(Product).filter(Product.is_deleted == 0)
    total_products = product_base.count()
    today_products = product_base.filter(Product.created_at >= today_start).count()
    week_products = product_base.filter(Product.created_at >= week_start).count()

    status_rows = (
        product_base
        .with_entities(Product.status, func.count())
        .group_by(Product.status)
        .all()
    )
    product_by_status = {s: c for s, c in status_rows}

    region_rows = (
        product_base
        .with_entities(Product.region, func.count())
        .group_by(Product.region)
        .all()
    )
    product_by_region = {r: c for r, c in region_rows}

    # ── 采集任务统计 ──
    crawl_status_rows = (
        db.query(CrawlTask.status, func.count())
        .group_by(CrawlTask.status)
        .all()
    )
    crawl_by_status = {s: c for s, c in crawl_status_rows}

    # ── 拼多多比价统计 ──
    total_matches = db.query(PddMatch).count()
    confirmed_matches = db.query(PddMatch).filter(PddMatch.is_confirmed == 1).count()
    products_with_match = (
        db.query(func.count(distinct(PddMatch.product_id)))
        .scalar()
    )

    match_source_rows = (
        db.query(PddMatch.match_source, func.count())
        .group_by(PddMatch.match_source)
        .all()
    )
    match_by_source = {s: c for s, c in match_source_rows}

    # ── 利润统计 ──
    latest_profit_sub = (
        db.query(
            ProfitRecord.product_id,
            func.max(ProfitRecord.id).label("max_id"),
        )
        .group_by(ProfitRecord.product_id)
        .subquery()
    )
    latest_profits = (
        db.query(ProfitRecord)
        .join(latest_profit_sub, ProfitRecord.id == latest_profit_sub.c.max_id)
        .all()
    )
    products_with_profit = len(latest_profits)
    if latest_profits:
        profit_values = [float(p.profit) for p in latest_profits]
        profit_rates = [float(p.profit_rate) for p in latest_profits]
        avg_profit = sum(profit_values) / len(profit_values)
        avg_profit_rate = sum(profit_rates) / len(profit_rates)
        positive_profit = sum(1 for p in profit_values if p > 0)
        high_margin = sum(1 for r in profit_rates if r >= 0.2)
    else:
        avg_profit = 0
        avg_profit_rate = 0
        positive_profit = 0
        high_margin = 0

    # ── 拍照购任务统计 ──
    photo_status_rows = (
        db.query(PhotoSearchTask.status, func.count())
        .group_by(PhotoSearchTask.status)
        .all()
    )
    photo_by_status = {s: c for s, c in photo_status_rows}
    photo_total = sum(photo_by_status.values())
    photo_success = photo_by_status.get("success", 0)

    # ── 设备统计 ──
    device_status_rows = (
        db.query(Device.status, func.count())
        .group_by(Device.status)
        .all()
    )
    device_by_status = {s: c for s, c in device_status_rows}

    # ── 近7天每日新增商品趋势 ──
    daily_trend = []
    for i in range(6, -1, -1):
        day = today_start - timedelta(days=i)
        day_end = day + timedelta(days=1)
        count = product_base.filter(
            and_(Product.created_at >= day, Product.created_at < day_end)
        ).count()
        daily_trend.append({"date": day.strftime("%m-%d"), "count": count})

    # ── 最近添加的商品 ──
    recent_products = (
        product_base
        .order_by(Product.created_at.desc())
        .limit(8)
        .all()
    )
    recent_list = [
        {
            "id": p.id,
            "title": p.title[:60] if p.title else "",
            "price": float(p.price) if p.price else 0,
            "currency": p.currency,
            "price_cny": float(p.price_cny) if p.price_cny else None,
            "region": p.region,
            "status": p.status,
            "sales_volume": p.sales_volume,
            "main_image_url": p.main_image_url,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in recent_products
    ]

    return Response(data={
        "products": {
            "total": total_products,
            "today": today_products,
            "week": week_products,
            "by_status": product_by_status,
            "by_region": product_by_region,
        },
        "crawl_tasks": {
            "by_status": crawl_by_status,
            "total": sum(crawl_by_status.values()),
        },
        "pdd_matches": {
            "total": total_matches,
            "confirmed": confirmed_matches,
            "products_with_match": products_with_match,
            "match_rate": round(products_with_match / total_products, 4) if total_products else 0,
            "by_source": match_by_source,
        },
        "profit": {
            "products_calculated": products_with_profit,
            "avg_profit": round(avg_profit, 2),
            "avg_profit_rate": round(avg_profit_rate, 4),
            "positive_count": positive_profit,
            "high_margin_count": high_margin,
        },
        "photo_search": {
            "total": photo_total,
            "success": photo_success,
            "success_rate": round(photo_success / photo_total, 4) if photo_total else 0,
            "by_status": photo_by_status,
        },
        "devices": {
            "total": sum(device_by_status.values()),
            "by_status": device_by_status,
        },
        "daily_trend": daily_trend,
        "recent_products": recent_list,
    })
