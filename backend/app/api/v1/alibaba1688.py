from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.common import Response
from app.schemas.alibaba1688_match import (
    Alibaba1688MatchCreate, Alibaba1688MatchUpdate, Alibaba1688MatchOut,
    Alibaba1688BatchCreate,
)
from app.services import alibaba1688_service
from app.services import product_service

router = APIRouter(prefix="/1688", tags=["1688比价"])


def _check_product_ownership(db: Session, product_id: int, user_id: int):
    product = product_service.get_product(db, product_id, user_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product


@router.post("/products/batch", response_model=Response, summary="插件批量入库1688商品")
def batch_create(
    data: Alibaba1688BatchCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_product_ownership(db, data.product_id, current_user.id)
    count = alibaba1688_service.batch_create_from_plugin(db, data)
    return Response(message=f"成功入库 {count} 条1688商品数据")


@router.post("/matches", response_model=Response[Alibaba1688MatchOut], summary="手动添加1688匹配商品")
def add_match(
    data: Alibaba1688MatchCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_product_ownership(db, data.product_id, current_user.id)
    match = alibaba1688_service.add_1688_match(db, data)
    return Response(data=Alibaba1688MatchOut.model_validate(match))


@router.get("/matches/batch", response_model=Response[Dict[str, List[Alibaba1688MatchOut]]], summary="批量获取多个商品的1688匹配")
def get_matches_batch(
    product_ids: str = Query(..., description="逗号分隔的商品ID列表"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ids = [int(x.strip()) for x in product_ids.split(",") if x.strip().isdigit()]
    if not ids:
        return Response(data={})
    result = alibaba1688_service.get_1688_matches_batch(db, ids)
    return Response(data={
        str(pid): [Alibaba1688MatchOut.model_validate(m) for m in matches]
        for pid, matches in result.items()
    })


@router.get("/matches/{product_id}", response_model=Response[List[Alibaba1688MatchOut]], summary="获取商品的1688匹配列表")
def get_matches(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_product_ownership(db, product_id, current_user.id)
    matches = alibaba1688_service.get_1688_matches(db, product_id)
    return Response(data=[Alibaba1688MatchOut.model_validate(m) for m in matches])


@router.patch("/matches/{match_id}", response_model=Response[Alibaba1688MatchOut], summary="更新匹配结果（确认/设为主参照）")
def update_match(
    match_id: int,
    data: Alibaba1688MatchUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    match = alibaba1688_service.update_1688_match(db, match_id, data)
    if not match:
        raise HTTPException(status_code=404, detail="匹配记录不存在")
    return Response(data=Alibaba1688MatchOut.model_validate(match))


@router.delete("/matches/{match_id}", summary="删除匹配记录")
def delete_match(
    match_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ok = alibaba1688_service.delete_1688_match(db, match_id)
    if not ok:
        raise HTTPException(status_code=404, detail="匹配记录不存在")
    return Response(message="删除成功")
