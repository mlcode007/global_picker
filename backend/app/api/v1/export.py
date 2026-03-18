from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from app.database import get_db
from app.services.export_service import export_products_excel

router = APIRouter(prefix="/export", tags=["报表导出"])


@router.get("/products", summary="导出商品比价报表（Excel）")
def export_products(
    ids: Optional[str] = Query(None, description="商品ID列表，逗号分隔，不传则导出全部"),
    db: Session = Depends(get_db),
):
    product_ids = [int(i) for i in ids.split(",") if i.strip()] if ids else None
    excel_bytes = export_products_excel(db, product_ids)
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=global_picker_report.xlsx"},
    )
