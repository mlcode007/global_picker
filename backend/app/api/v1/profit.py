from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import Response
from app.schemas.profit import ProfitCalcRequest, ProfitOut
from app.services import profit_service

router = APIRouter(prefix="/profit", tags=["利润计算"])


@router.post("/calculate", response_model=Response[ProfitOut], summary="计算并保存利润")
def calculate(req: ProfitCalcRequest, db: Session = Depends(get_db)):
    record = profit_service.calculate_profit(db, req)
    return Response(data=ProfitOut.model_validate(record))


@router.get("/{product_id}/history", response_model=Response[List[ProfitOut]], summary="商品利润计算历史")
def profit_history(product_id: int, db: Session = Depends(get_db)):
    records = profit_service.get_profit_history(db, product_id)
    return Response(data=[ProfitOut.model_validate(r) for r in records])


@router.get("/exchange-rates", summary="获取汇率列表")
def exchange_rates(db: Session = Depends(get_db)):
    from app.models.exchange_rate import ExchangeRate
    rates = db.query(ExchangeRate).all()
    return Response(data=[{"currency": r.currency, "rate_to_cny": float(r.rate_to_cny)} for r in rates])


@router.post("/refresh-price-cny", summary="根据当前汇率重算所有商品的 price_cny")
def refresh_price_cny(db: Session = Depends(get_db)):
    from app.models.product import Product
    from app.services.exchange_rate_service import convert_to_cny, currency_for_region
    products = db.query(Product).filter(Product.is_deleted == 0, Product.price > 0).all()
    count = 0
    for p in products:
        if p.region:
            correct = currency_for_region(p.region)
            if correct and correct != p.currency:
                p.currency = correct
        cny = convert_to_cny(db, p.price, p.currency)
        if cny is not None and cny != p.price_cny:
            p.price_cny = cny
            count += 1
    db.commit()
    return Response(data={"updated": count, "total": len(products)})
