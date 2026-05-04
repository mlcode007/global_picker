from typing import List
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.common import Response
from app.schemas.profit import ProfitCalcRequest, ProfitOut
from app.services import profit_service, product_service

router = APIRouter(prefix="/profit", tags=["利润计算"])


class ExchangeRateUpdate(BaseModel):
    rate_to_cny: Decimal = Field(..., gt=0, description="兑换人民币汇率")


class ExchangeRateBatchUpdate(BaseModel):
    rates: dict[str, Decimal] = Field(..., description="币种代码到汇率的映射")


@router.post("/calculate", response_model=Response[ProfitOut], summary="计算并保存利润")
def calculate(
    req: ProfitCalcRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = profit_service.calculate_profit(db, req)
    return Response(data=ProfitOut.model_validate(record))


@router.get("/{product_id}/history", response_model=Response[List[ProfitOut]], summary="商品利润计算历史")
def profit_history(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product_service.get_product(db, product_id, current_user.id)
    records = profit_service.get_profit_history(db, product_id)
    return Response(data=[ProfitOut.model_validate(r) for r in records])


@router.get("/exchange-rates", summary="获取汇率列表")
def exchange_rates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models.exchange_rate import ExchangeRate
    rates = db.query(ExchangeRate).all()
    return Response(data=[{
        "currency": r.currency,
        "rate_to_cny": float(r.rate_to_cny),
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    } for r in rates])


@router.put("/exchange-rates/{currency}", summary="更新单个汇率")
def update_exchange_rate(
    currency: str,
    req: ExchangeRateUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models.exchange_rate import ExchangeRate
    from app.services.exchange_rate_service import clear_cache
    rate = db.query(ExchangeRate).filter(ExchangeRate.currency == currency.upper()).first()
    if not rate:
        raise HTTPException(status_code=404, detail=f"币种 {currency} 不存在")
    rate.rate_to_cny = req.rate_to_cny
    db.commit()
    db.refresh(rate)
    clear_cache()
    return Response(data={"currency": rate.currency, "rate_to_cny": float(rate.rate_to_cny)})


@router.put("/exchange-rates", summary="批量更新汇率")
def batch_update_exchange_rates(
    req: ExchangeRateBatchUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models.exchange_rate import ExchangeRate
    from app.services.exchange_rate_service import clear_cache
    updated = []
    for currency, new_rate in req.rates.items():
        rate = db.query(ExchangeRate).filter(ExchangeRate.currency == currency.upper()).first()
        if rate:
            rate.rate_to_cny = new_rate
            updated.append({"currency": rate.currency, "rate_to_cny": float(rate.rate_to_cny)})
    db.commit()
    if updated:
        clear_cache()
    return Response(data={"updated": updated, "count": len(updated)})


@router.post("/refresh-price-cny", summary="根据当前汇率重算所有商品的 price_cny")
def refresh_price_cny(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models.product import Product
    from app.services.exchange_rate_service import convert_to_cny, currency_for_region
    products = db.query(Product).filter(
        Product.is_deleted == 0,
        Product.price > 0,
        Product.user_id == current_user.id,
    ).all()
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
