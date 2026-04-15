from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, field_validator


class PhotoSearchTaskCreate(BaseModel):
    product_id: int
    image_index: int = 0
    fetch_pdd_links: bool = True
    # 单次任务最多入库的拼多多候选条数（与列表「单次最多」一致）
    max_candidates: int = 4

    @field_validator("max_candidates", mode="before")
    @classmethod
    def _clamp_max_candidates(cls, v):
        if v is None:
            return 4
        try:
            n = int(v)
        except (TypeError, ValueError):
            return 4
        return max(1, min(n, 50))


class PhotoSearchTaskOut(BaseModel):
    id: int
    product_id: int
    device_id: Optional[str]
    status: str
    step: Optional[str]
    source_image_url: Optional[str]
    attempt_count: int
    max_attempts: int
    max_candidates: int = 4
    candidates_found: int
    candidates_saved: int
    error_code: Optional[str]
    error_message: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    elapsed_ms: Optional[int]
    fetch_pdd_links: bool = True
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("max_candidates", mode="before")
    @classmethod
    def _coerce_max_candidates_out(cls, v):
        if v is None:
            return 4
        try:
            return int(v)
        except (TypeError, ValueError):
            return 4

    @field_validator("fetch_pdd_links", mode="before")
    @classmethod
    def _coerce_fetch_pdd_links(cls, v):
        if v is None:
            return True
        if isinstance(v, bool):
            return v
        try:
            return bool(int(v))
        except (TypeError, ValueError):
            return True


class DeviceOut(BaseModel):
    id: int
    device_id: str
    device_name: Optional[str]
    device_type: str
    android_version: Optional[str]
    screen_width: Optional[int]
    screen_height: Optional[int]
    app_version: Optional[str]
    status: str
    current_task_id: Optional[int]
    last_heartbeat: Optional[datetime]
    error_count: int

    model_config = {"from_attributes": True}


class DeviceActionLogOut(BaseModel):
    id: int
    task_id: int
    device_id: str
    step: str
    action: str
    success: bool
    elapsed_ms: Optional[int]
    screenshot_path: Optional[str]
    xml_dump_path: Optional[str]
    message: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
