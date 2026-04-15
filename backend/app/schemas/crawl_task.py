from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.product import ProductOut


class CrawlTaskOut(BaseModel):
    id: int
    url: str
    status: str
    retry_count: int
    error_msg: Optional[str]
    status_detail: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    # 任务 status=done 时由接口填充，便于前端一次更新列表行
    product: Optional[ProductOut] = None

    model_config = {"from_attributes": True}
