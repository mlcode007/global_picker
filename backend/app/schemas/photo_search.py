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


class BatchPhotoSearchTaskCreate(BaseModel):
    """批量创建拍照购任务请求"""
    product_ids: List[int]
    image_index: int = 0
    fetch_pdd_links: bool = True
    max_candidates: int = 4
    # 并发度限制（默认使用所有可用设备）
    concurrency: Optional[int] = None

    @field_validator("max_candidates", mode="before")
    @classmethod
    def _clamp_batch_max_candidates(cls, v):
        if v is None:
            return 4
        try:
            n = int(v)
        except (TypeError, ValueError):
            return 4
        return max(1, min(n, 50))


class BatchTaskResult(BaseModel):
    """批量任务创建结果"""
    batch_id: str
    total_count: int
    created_count: int
    skipped_count: int
    failed_count: int
    task_ids: List[int]
    skipped_products: List[int] = []
    failed_products: List[int] = []


class BatchTaskStatusOut(BaseModel):
    """批量任务状态汇总"""
    batch_id: str
    total_count: int
    pending_count: int
    running_count: int
    success_count: int
    failed_count: int
    cancelled_count: int
    progress: float
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


class TaskQueueStatus(BaseModel):
    """任务队列状态"""
    queued_count: int
    running_count: int
    success_count: int
    failed_count: int
    available_devices: int
    busy_devices: int
