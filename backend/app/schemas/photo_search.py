from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel


class PhotoSearchTaskCreate(BaseModel):
    product_id: int
    image_index: int = 0


class PhotoSearchTaskOut(BaseModel):
    id: int
    product_id: int
    device_id: Optional[str]
    status: str
    step: Optional[str]
    source_image_url: Optional[str]
    attempt_count: int
    max_attempts: int
    candidates_found: int
    candidates_saved: int
    error_code: Optional[str]
    error_message: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    elapsed_ms: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


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
