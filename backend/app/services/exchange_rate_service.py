"""汇率服务：币种换算 + region→currency 映射"""
from __future__ import annotations

import threading
import time
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy.orm import Session

from app.models.exchange_rate import ExchangeRate

REGION_CURRENCY_MAP: dict[str, str] = {
    "PH": "PHP",
    "MY": "MYR",
    "TH": "THB",
    "SG": "SGD",
    "ID": "IDR",
    "VN": "VND",
    "US": "USD",
    "GB": "GBP",
    "JP": "JPY",
    "KR": "KRW",
    "BR": "BRL",
    "MX": "MXN",
    "SA": "SAR",
}

_cache: dict[str, Decimal] = {}
_cache_ts: float = 0
_cache_lock = threading.Lock()
_CACHE_TTL = 300  # 5 分钟


def _refresh_cache(db: Session) -> None:
    global _cache_ts
    rows = db.query(ExchangeRate).all()
    new_cache = {r.currency: r.rate_to_cny for r in rows}
    with _cache_lock:
        _cache.clear()
        _cache.update(new_cache)
        _cache_ts = time.time()


def get_rate(db: Session, currency: str) -> Optional[Decimal]:
    """获取某币种到 CNY 的汇率，带内存缓存。"""
    if currency == "CNY":
        return Decimal("1")
    now = time.time()
    if now - _cache_ts > _CACHE_TTL:
        _refresh_cache(db)
    return _cache.get(currency.upper())


def convert_to_cny(db: Session, amount: Decimal, currency: str) -> Optional[Decimal]:
    """将外币金额换算为人民币，返回保留两位小数的 Decimal。"""
    rate = get_rate(db, currency)
    if rate is None:
        return None
    return (amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def currency_for_region(region: str) -> Optional[str]:
    """根据 region code 返回对应币种。"""
    return REGION_CURRENCY_MAP.get(region.upper())
