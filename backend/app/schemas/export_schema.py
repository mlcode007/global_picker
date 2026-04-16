from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class ExportProductsRequest(BaseModel):
    """导出商品为 Excel：勾选导出时传 product_ids；全量导出时 export_all=true。"""

    product_ids: Optional[List[int]] = Field(
        None,
        description="所选商品主键 ID（与 export_all 二选一），条数以实际勾选为准",
    )
    export_all: bool = Field(False, description="为 true 时导出当前账号下全部未删除商品")
    fields: Optional[List[str]] = Field(
        None,
        description="要导出的字段 key 列表，不传则导出全部可选字段",
    )

    @model_validator(mode="after")
    def ids_or_export_all(self):
        if self.export_all:
            return self
        if not self.product_ids or len(self.product_ids) < 1:
            raise ValueError("请传入 product_ids，或使用 export_all 导出全部")
        return self
