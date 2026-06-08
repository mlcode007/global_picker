"""
1688匹配服务
- 处理1688商品匹配数据的入库、查询、更新
- 与拼多多匹配类似，但独立存储
"""
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.alibaba1688_match import Alibaba1688Match
from app.models.product import Product
from app.schemas.alibaba1688_match import (
    Alibaba1688MatchCreate, Alibaba1688MatchUpdate, Alibaba1688BatchCreate,
)
from app.config import get_settings

logger = logging.getLogger(__name__)


def _update_product_profit(db: Session, product_id: int, price_1688: Decimal, match_score=None):
    """根据主参照1688价格更新商品的预估利润和主参照相似度"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product or not product.price_cny or product.price_cny <= 0:
        return
    profit = (product.price_cny - price_1688).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    rate = (profit / product.price_cny).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    product.estimated_profit = profit
    product.profit_rate = rate
    if match_score is not None:
        product.primary_match_score = match_score
    logger.info("Product #%d profit updated from 1688: %.2f (rate %.4f, score %s)", product_id, profit, rate, match_score)


def refresh_product_profit_from_primary_1688(db: Session, product_id: int) -> None:
    """TikTok 标价或人民币价变化后，若存在主参照1688匹配，则按当前 price_cny 重算预估利润。"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product or not product.price_cny or product.price_cny <= 0:
        return
    primary = (
        db.query(Alibaba1688Match)
        .filter(Alibaba1688Match.product_id == product_id, Alibaba1688Match.is_primary == 1)
        .first()
    )
    if not primary:
        return
    _update_product_profit(db, product_id, primary.price, primary.match_score)


def add_1688_match(db: Session, data: Alibaba1688MatchCreate) -> Alibaba1688Match:
    if data.is_primary:
        db.query(Alibaba1688Match).filter(
            Alibaba1688Match.product_id == data.product_id,
            Alibaba1688Match.is_primary == 1,
        ).update({"is_primary": 0})

    match = Alibaba1688Match(**data.model_dump())
    db.add(match)
    db.flush()

    if data.is_primary:
        _update_product_profit(db, data.product_id, match.price, match.match_score)

    db.commit()
    db.refresh(match)
    return match


def get_1688_matches(db: Session, product_id: int) -> List[Alibaba1688Match]:
    return (
        db.query(Alibaba1688Match)
        .filter(Alibaba1688Match.product_id == product_id)
        .order_by(Alibaba1688Match.is_primary.desc(), Alibaba1688Match.created_at.desc())
        .all()
    )


def update_1688_match(db: Session, match_id: int, data: Alibaba1688MatchUpdate) -> Optional[Alibaba1688Match]:
    match = db.query(Alibaba1688Match).filter(Alibaba1688Match.id == match_id).first()
    if not match:
        return None

    if data.is_primary == 1:
        db.query(Alibaba1688Match).filter(
            Alibaba1688Match.product_id == match.product_id,
            Alibaba1688Match.is_primary == 1,
        ).update({"is_primary": 0})

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(match, field, value)

    if data.is_primary == 1:
        _update_product_profit(db, match.product_id, match.price, match.match_score)

    db.commit()
    db.refresh(match)
    return match


def get_1688_matches_batch(db: Session, product_ids: List[int]) -> dict:
    """批量获取多个商品的1688匹配列表，返回 {product_id: [matches]}"""
    if not product_ids:
        return {}
    matches = (
        db.query(Alibaba1688Match)
        .filter(Alibaba1688Match.product_id.in_(product_ids))
        .order_by(Alibaba1688Match.is_primary.desc(), Alibaba1688Match.created_at.desc())
        .all()
    )
    result = {pid: [] for pid in product_ids}
    for m in matches:
        if m.product_id in result:
            result[m.product_id].append(m)
    return result


def delete_1688_match(db: Session, match_id: int) -> bool:
    match = db.query(Alibaba1688Match).filter(Alibaba1688Match.id == match_id).first()
    if not match:
        return False
    db.delete(match)
    db.commit()
    return True


def batch_create_from_plugin(db: Session, data: Alibaba1688BatchCreate) -> int:
    """插件批量入库1688商品数据

    - 价格取代发价(consignPrice)优先，其次展示价(price)
    - 按 (product_id, offer_id) 去重：已存在则更新关键信息，不重复插入
    - 若该商品当前无主参照，则自动把价格最低的新匹配设为主参照并刷新预估利润
    - 优先使用请求中的 sync_limit，其次使用配置 ALIBABA1688_SYNC_LIMIT，超过数量的商品将被忽略
    - page > 1 时直接跳过，不入库
    - 计算图片相似度并存储，供前端展示
    """
    from app.services.image_similarity_service import calculate_image_similarity

    # 第二页及以上不入库
    if data.page and data.page > 1:
        logger.info(
            "插件批量入库1688商品: product_id=%d, page=%d, 跳过入库",
            data.product_id, data.page
        )
        return 0

    settings = get_settings()
    sync_limit = data.sync_limit if data.sync_limit is not None else settings.ALIBABA1688_SYNC_LIMIT

    product_id = data.product_id
    created = 0
    updated_existing = 0

    # 获取TikTok商品主图
    product = db.query(Product).filter(Product.id == product_id).first()
    source_image_url = product.main_image_url if product else None

    has_primary = (
        db.query(Alibaba1688Match)
        .filter(Alibaba1688Match.product_id == product_id, Alibaba1688Match.is_primary == 1)
        .first()
        is not None
    )
    # 记录所有新匹配，用于后续选择最佳主参照
    # 选择规则：相似度最高优先，相似度相同时选价格最低
    new_matches = []

    for item in data.products:
        if created >= sync_limit:
            logger.info(
                "插件批量入库1688商品: product_id=%d, 已达同步上限 %d，忽略剩余商品",
                product_id, sync_limit
            )
            break

        price_val = item.price or item.consignPrice or 0
        price = Decimal(str(price_val)) if price_val and price_val > 0 else Decimal("0")
        offer_id = item.offerId or None
        good_rates = Decimal(str(item.goodRates)) if item.goodRates else None
        images = ",".join(item.images) if item.images else None

        # 计算图片相似度（如果有源图和候选图）
        match_score = None
        if source_image_url and item.mainImage:
            match_score = calculate_image_similarity(source_image_url, item.mainImage)

        # 按 offer_id 去重（offer_id 为空时按标题兜底）
        existing = None
        if offer_id:
            existing = (
                db.query(Alibaba1688Match)
                .filter(
                    Alibaba1688Match.product_id == product_id,
                    Alibaba1688Match.offer_id == offer_id,
                )
                .first()
            )
        elif item.title:
            existing = (
                db.query(Alibaba1688Match)
                .filter(
                    Alibaba1688Match.product_id == product_id,
                    Alibaba1688Match.title == item.title,
                )
                .first()
            )

        if existing:
            changed = False
            if price > 0 and existing.price != price:
                existing.price = price
                changed = True
            if item.mainImage and existing.main_image != item.mainImage:
                existing.main_image = item.mainImage
                changed = True
            if item.last30DaysSales and existing.last30_days_sales != item.last30DaysSales:
                existing.last30_days_sales = item.last30DaysSales
                changed = True
            if item.totalSales and existing.total_sales != item.totalSales:
                existing.total_sales = item.totalSales
                changed = True
            if item.companyName and existing.company_name != item.companyName:
                existing.company_name = item.companyName
                changed = True
            # 更新相似度分数
            if match_score is not None:
                existing.match_score = match_score
                changed = True
            # 包邮字段：始终更新（不依赖 changed 标记）
            if item.isFreeShipping is not None:
                existing.is_free_shipping = bool(item.isFreeShipping)
            if item.minFreight is not None:
                existing.min_freight = float(item.minFreight)
            if changed:
                # 若被更新的是主参照，价格变动需同步刷新利润
                if existing.is_primary == 1 and price > 0:
                    _update_product_profit(db, product_id, existing.price, existing.match_score)
                updated_existing += 1
            continue

        match = Alibaba1688Match(
            product_id=product_id,
            offer_id=offer_id,
            member_id=item.memberId or None,
            title=item.title or "",
            main_image=item.mainImage or None,
            images=images,
            last30_days_sales=item.last30DaysSales or None,
            total_sales=item.totalSales or None,
            good_rates=good_rates,
            repurchase_rate=item.repurchaseRate or None,
            tp_year=item.tpYear or None,
            free_return_in7d=item.freeReturnIn7d or None,
            support_waybill=item.supportWaybill or None,
            company_name=item.companyName or None,
            is_free_shipping=bool(item.isFreeShipping) if item.isFreeShipping is not None else False,
            min_freight=float(item.minFreight) if item.minFreight is not None else 0.0,
            price=price,
            match_source="image_search",
            match_score=match_score,
            is_confirmed=0,
            is_primary=0,
        )
        db.add(match)
        created += 1

        # 记录新匹配，用于后续选择最佳主参照
        new_matches.append(match)

    # 如果没有主参照，从新匹配中选择最佳设为主参照
    # 选择规则：相似度最高优先，相似度相同时选价格最低
    if not has_primary and new_matches:
        best_match = max(
            new_matches,
            key=lambda m: (m.match_score or 0, -float(m.price) if m.price and m.price > 0 else 0)
        )
        if best_match.price and best_match.price > 0:
            best_match.is_primary = 1
            _update_product_profit(db, product_id, best_match.price, best_match.match_score)

    if created or updated_existing:
        db.commit()

    # 日志记录放在 commit 之后，确保 id 已生成
    if not has_primary and new_matches:
        best_match = max(
            new_matches,
            key=lambda m: (m.match_score or 0, -float(m.price) if m.price and m.price > 0 else 0)
        )
        if best_match.price and best_match.price > 0:
            logger.info(
                "自动设置主参照: product_id=%d, match_id=%d, score=%.4f, price=%.2f",
                product_id, best_match.id, best_match.match_score or 0, best_match.price
            )

    logger.info(
        "插件批量入库1688商品: product_id=%d, 新增=%d, 更新=%d", product_id, created, updated_existing
    )
    return created


def recalculate_similarity_for_product(db: Session, product_id: int) -> dict:
    """为指定商品的1688匹配重新计算图片相似度

    当TikTok商品主图爬取完成后，调用此函数补算之前缺失的相似度分数。

    Returns:
        {"calculated": int, "skipped": int, "errors": int}
    """
    from app.services.image_similarity_service import calculate_image_similarity

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product or not product.main_image_url:
        logger.warning("Product #%d has no main_image_url, skip similarity calculation", product_id)
        return {"calculated": 0, "skipped": 0, "errors": 0}

    source_image_url = product.main_image_url
    matches = db.query(Alibaba1688Match).filter(
        Alibaba1688Match.product_id == product_id,
        Alibaba1688Match.main_image.isnot(None),
    ).all()

    calculated = 0
    skipped = 0
    errors = 0

    for match in matches:
        if not match.main_image:
            skipped += 1
            continue

        try:
            score = calculate_image_similarity(source_image_url, match.main_image)
            if score is not None:
                match.match_score = score
                calculated += 1
            else:
                errors += 1
        except Exception as e:
            logger.error("Failed to calculate similarity for match #%d: %s", match.id, e)
            errors += 1

    if calculated > 0:
        db.commit()

    logger.info(
        "Recalculated similarity for product #%d: calculated=%d, skipped=%d, errors=%d",
        product_id, calculated, skipped, errors,
    )
    return {"calculated": calculated, "skipped": skipped, "errors": errors}


def recalculate_similarity_batch(db: Session, product_ids: List[int]) -> dict:
    """批量为多个商品重新计算1688匹配的图片相似度

    Returns:
        {"total": int, "results": {product_id: {"calculated": int, "skipped": int, "errors": int}}}
    """
    results = {}
    total_calculated = 0

    for pid in product_ids:
        result = recalculate_similarity_for_product(db, pid)
        results[pid] = result
        total_calculated += result["calculated"]

    return {"total": total_calculated, "results": results}
