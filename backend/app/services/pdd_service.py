"""
拼多多匹配服务
- 当前提供手动录入匹配结果
- 后续可接入：图片搜索（百度图片/必应）、关键词搜索等自动化抓取
"""
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.pdd_match import PddMatch
from app.models.product import Product
from app.schemas.pdd_match import PddMatchCreate, PddMatchUpdate

logger = logging.getLogger(__name__)


def _update_product_profit(db: Session, product_id: int, pdd_price: Decimal):
    """根据主参照拼多多价格更新商品的预估利润"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product or not product.price_cny or product.price_cny <= 0:
        return
    profit = (product.price_cny - pdd_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    rate = (profit / product.price_cny).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    product.estimated_profit = profit
    product.profit_rate = rate
    logger.info("Product #%d profit updated: %.2f (rate %.4f)", product_id, profit, rate)


def refresh_product_profit_from_primary_pdd(db: Session, product_id: int) -> None:
    """TikTok 标价或人民币价变化后，若存在主参照拼多多匹配，则按当前 price_cny 重算预估利润。"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product or not product.price_cny or product.price_cny <= 0:
        return
    primary = (
        db.query(PddMatch)
        .filter(PddMatch.product_id == product_id, PddMatch.is_primary == 1)
        .first()
    )
    if not primary:
        return
    _update_product_profit(db, product_id, primary.pdd_price)


def add_pdd_match(db: Session, data: PddMatchCreate) -> PddMatch:
    if data.is_primary:
        db.query(PddMatch).filter(
            PddMatch.product_id == data.product_id,
            PddMatch.is_primary == 1,
        ).update({"is_primary": 0})

    match = PddMatch(**data.model_dump())
    db.add(match)
    db.flush()

    if data.is_primary:
        _update_product_profit(db, data.product_id, match.pdd_price)

    db.commit()
    db.refresh(match)
    return match


def get_pdd_matches(db: Session, product_id: int) -> List[PddMatch]:
    return (
        db.query(PddMatch)
        .filter(PddMatch.product_id == product_id)
        .order_by(PddMatch.is_primary.desc(), PddMatch.created_at.desc())
        .all()
    )


def update_pdd_match(db: Session, match_id: int, data: PddMatchUpdate) -> Optional[PddMatch]:
    match = db.query(PddMatch).filter(PddMatch.id == match_id).first()
    if not match:
        return None

    if data.is_primary == 1:
        db.query(PddMatch).filter(
            PddMatch.product_id == match.product_id,
            PddMatch.is_primary == 1,
        ).update({"is_primary": 0})

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(match, field, value)

    if data.is_primary == 1:
        _update_product_profit(db, match.product_id, match.pdd_price)

    db.commit()
    db.refresh(match)
    return match


def get_pdd_matches_batch(db: Session, product_ids: List[int]) -> dict:
    """批量获取多个商品的拼多多匹配列表，返回 {product_id: [matches]}"""
    if not product_ids:
        return {}
    matches = (
        db.query(PddMatch)
        .filter(PddMatch.product_id.in_(product_ids))
        .order_by(PddMatch.is_primary.desc(), PddMatch.created_at.desc())
        .all()
    )
    result = {pid: [] for pid in product_ids}
    for m in matches:
        if m.product_id in result:
            result[m.product_id].append(m)
    return result


def delete_pdd_match(db: Session, match_id: int) -> bool:
    match = db.query(PddMatch).filter(PddMatch.id == match_id).first()
    if not match:
        return False
    db.delete(match)
    db.commit()
    return True
