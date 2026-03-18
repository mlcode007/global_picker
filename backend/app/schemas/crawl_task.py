from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class CrawlTaskOut(BaseModel):
    id: int
    url: str
    status: str
    retry_count: int
    error_msg: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
