from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import Response
from app.schemas.pdd_match import PddMatchCreate, PddMatchUpdate, PddMatchOut
from app.services import pdd_service

router = APIRouter(prefix="/pdd", tags=["拼多多比价"])


@router.post("/matches", response_model=Response[PddMatchOut], summary="手动添加拼多多匹配商品")
def add_match(data: PddMatchCreate, db: Session = Depends(get_db)):
    match = pdd_service.add_pdd_match(db, data)
    return Response(data=PddMatchOut.model_validate(match))


@router.get("/matches/{product_id}", response_model=Response[List[PddMatchOut]], summary="获取商品的拼多多匹配列表")
def get_matches(product_id: int, db: Session = Depends(get_db)):
    matches = pdd_service.get_pdd_matches(db, product_id)
    return Response(data=[PddMatchOut.model_validate(m) for m in matches])


@router.patch("/matches/{match_id}", response_model=Response[PddMatchOut], summary="更新匹配结果（确认/设为主参照）")
def update_match(match_id: int, data: PddMatchUpdate, db: Session = Depends(get_db)):
    match = pdd_service.update_pdd_match(db, match_id, data)
    if not match:
        raise HTTPException(status_code=404, detail="匹配记录不存在")
    return Response(data=PddMatchOut.model_validate(match))


@router.delete("/matches/{match_id}", summary="删除匹配记录")
def delete_match(match_id: int, db: Session = Depends(get_db)):
    ok = pdd_service.delete_pdd_match(db, match_id)
    if not ok:
        raise HTTPException(status_code=404, detail="匹配记录不存在")
    return Response(message="删除成功")
