"""报表导出服务：生成 Excel 文件"""
import io
from typing import List
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.pdd_match import PddMatch
from app.models.profit_record import ProfitRecord


def export_products_excel(db: Session, product_ids: List[int] = None) -> bytes:
    """导出商品比价报表为 Excel"""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    query = db.query(Product).filter(Product.is_deleted == 0)
    if product_ids:
        query = query.filter(Product.id.in_(product_ids))
    products = query.order_by(Product.created_at.desc()).all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "选品报表"

    headers = [
        "商品ID", "商品标题", "TikTok链接", "区域", "TikTok售价", "货币",
        "折合人民币", "TikTok销量", "评分", "店铺", "选品状态",
        "拼多多价格(主)", "拼多多店铺(主)", "利润(最新)", "利润率(最新)", "备注", "添加时间",
    ]

    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    for row, p in enumerate(products, 2):
        primary_match = next(
            (m for m in p.pdd_matches if m.is_primary), None
        ) or (p.pdd_matches[0] if p.pdd_matches else None)

        latest_profit = (
            db.query(ProfitRecord)
            .filter(ProfitRecord.product_id == p.id)
            .order_by(ProfitRecord.created_at.desc())
            .first()
        )

        ws.cell(row=row, column=1, value=p.id)
        ws.cell(row=row, column=2, value=p.title)
        ws.cell(row=row, column=3, value=p.tiktok_url)
        ws.cell(row=row, column=4, value=p.region)
        ws.cell(row=row, column=5, value=float(p.price) if p.price else None)
        ws.cell(row=row, column=6, value=p.currency)
        ws.cell(row=row, column=7, value=float(p.price_cny) if p.price_cny else None)
        ws.cell(row=row, column=8, value=p.sales_volume)
        ws.cell(row=row, column=9, value=float(p.rating) if p.rating else None)
        ws.cell(row=row, column=10, value=p.shop_name)
        ws.cell(row=row, column=11, value=p.status)
        ws.cell(row=row, column=12, value=float(primary_match.pdd_price) if primary_match else None)
        ws.cell(row=row, column=13, value=primary_match.pdd_shop_name if primary_match else None)
        ws.cell(row=row, column=14, value=float(latest_profit.profit) if latest_profit else None)
        ws.cell(row=row, column=15, value=f"{float(latest_profit.profit_rate)*100:.2f}%" if latest_profit else None)
        ws.cell(row=row, column=16, value=p.remark)
        ws.cell(row=row, column=17, value=p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else None)

    for col in ws.columns:
        max_len = max((len(str(cell.value or "")) for cell in col), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 50)

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
