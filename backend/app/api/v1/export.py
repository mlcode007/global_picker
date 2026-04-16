import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.export_schema import ExportProductsRequest
from app.services.export_service import export_products_excel

router = APIRouter(prefix="/export", tags=["报表导出"])


@router.post("/products", summary="导出所选商品（Excel）")
def export_products(
    body: ExportProductsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        excel_bytes = export_products_excel(
            db,
            user_id=current_user.id,
            fields=body.fields,
            product_ids=body.product_ids,
            export_all=body.export_all,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    filename = f"tiktok_products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
