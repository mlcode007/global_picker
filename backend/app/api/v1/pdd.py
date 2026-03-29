from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.common import Response
from app.schemas.pdd_match import PddMatchCreate, PddMatchUpdate, PddMatchOut
from app.services import pdd_service
from app.services import product_service

router = APIRouter(prefix="/pdd", tags=["拼多多比价"])


def _check_product_ownership(db: Session, product_id: int, user_id: int):
    product = product_service.get_product(db, product_id, user_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product


@router.post("/matches", response_model=Response[PddMatchOut], summary="手动添加拼多多匹配商品")
def add_match(
    data: PddMatchCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_product_ownership(db, data.product_id, current_user.id)
    match = pdd_service.add_pdd_match(db, data)
    return Response(data=PddMatchOut.model_validate(match))


@router.get("/matches/{product_id}", response_model=Response[List[PddMatchOut]], summary="获取商品的拼多多匹配列表")
def get_matches(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_product_ownership(db, product_id, current_user.id)
    matches = pdd_service.get_pdd_matches(db, product_id)
    return Response(data=[PddMatchOut.model_validate(m) for m in matches])


@router.patch("/matches/{match_id}", response_model=Response[PddMatchOut], summary="更新匹配结果（确认/设为主参照）")
def update_match(
    match_id: int,
    data: PddMatchUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    match = pdd_service.update_pdd_match(db, match_id, data)
    if not match:
        raise HTTPException(status_code=404, detail="匹配记录不存在")
    return Response(data=PddMatchOut.model_validate(match))


@router.delete("/matches/{match_id}", summary="删除匹配记录")
def delete_match(
    match_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ok = pdd_service.delete_pdd_match(db, match_id)
    if not ok:
        raise HTTPException(status_code=404, detail="匹配记录不存在")
    return Response(message="删除成功")
