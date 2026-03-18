"""
拼多多匹配服务
- 当前提供手动录入匹配结果
- 后续可接入：图片搜索（百度图片/必应）、关键词搜索等自动化抓取
"""
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.pdd_match import PddMatch
from app.schemas.pdd_match import PddMatchCreate, PddMatchUpdate


def add_pdd_match(db: Session, data: PddMatchCreate) -> PddMatch:
    if data.is_primary:
        db.query(PddMatch).filter(
            PddMatch.product_id == data.product_id,
            PddMatch.is_primary == 1,
        ).update({"is_primary": 0})

    match = PddMatch(**data.model_dump())
    db.add(match)
    db.commit()
    db.refresh(match)
    return match


def get_pdd_matches(db: Session, product_id: int) -> List[PddMatch]:
    return (
        db.query(PddMatch)
        .filter(PddMatch.product_id == product_id)
        .order_by(PddMatch.is_primary.desc(), PddMatch.match_confidence.desc())
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
    db.commit()
    db.refresh(match)
    return match


def delete_pdd_match(db: Session, match_id: int) -> bool:
    match = db.query(PddMatch).filter(PddMatch.id == match_id).first()
    if not match:
        return False
    db.delete(match)
    db.commit()
    return True
