from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class PagedResponse(BaseModel, Generic[T]):
    """统一分页响应格式"""
    total: int
    page: int
    page_size: int
    items: List[T]


class Response(BaseModel, Generic[T]):
    """统一响应格式"""
    code: int = 0
    message: str = "ok"
    data: Optional[T] = None
