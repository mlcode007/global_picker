import traceback
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.payment import PaymentOrder
from app.core.security import get_current_user
from app.services.alipay_service import AlipayService
from app.services.points_service import PointsManager

router = APIRouter(prefix="/payment", tags=["payment"])
alipay_service = None


def get_alipay_service():
    global alipay_service
    if alipay_service is None:
        alipay_service = AlipayService()
    return alipay_service


class CreatePaymentRequest(BaseModel):
    points: int


@router.post("/alipay/create")
def create_payment(
    request: CreatePaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    points = request.points
    amount = float(points)
    out_trade_no = f"GP{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8]}"
    subject = f"积分充值-{points}分"
    
    try:
        service = get_alipay_service()
        qr_code = service.create_qr_code_url(
            out_trade_no=out_trade_no,
            total_amount=str(amount),
            subject=subject
        )
        
        db_order = PaymentOrder(
            user_id=current_user.id,
            out_trade_no=out_trade_no,
            payment_method='alipay',
            amount=amount,
            points=points,
            status='pending',
            subject=subject,
            qr_code=qr_code
        )
        db.add(db_order)
        db.commit()
        
        return {
            "code": 0,
            "msg": "success",
            "data": {
                "out_trade_no": out_trade_no,
                "qr_code": qr_code,
                "amount": amount,
                "points": points
            }
        }
    except Exception as e:
        db.rollback()
        error_trace = traceback.format_exc()
        print(f"Payment error: {error_trace}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alipay/query")
def query_payment(
    request_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    out_trade_no = request_data.get("out_trade_no")
    if not out_trade_no:
        return {"code": -1, "msg": "缺少订单号", "data": None}
    
    try:
        service = get_alipay_service()
        result = service.query_order(out_trade_no=out_trade_no)
        
        trade_status = result.get("trade_status")
        db_order = db.query(PaymentOrder).filter(PaymentOrder.out_trade_no == out_trade_no).first()
        
        if trade_status == "TRADE_SUCCESS" or trade_status == "TRADE_FINISHED":
            if db_order and db_order.status == "pending":
                manager = PointsManager(db)
                manager.add_points(db_order.user_id, db_order.points, f"支付宝充值-{out_trade_no}")
                db_order.status = "paid"
                db_order.trade_no = result.get("trade_no")
                db_order.paid_at = datetime.now()
                db.commit()
            
            return {
                "code": 0,
                "msg": "支付成功",
                "data": {
                    "status": "paid",
                    "trade_status": trade_status
                }
            }
        elif trade_status == "WAIT_BUYER_PAY":
            return {
                "code": 0,
                "msg": "等待支付",
                "data": {
                    "status": "pending",
                    "trade_status": trade_status
                }
            }
        else:
            if db_order and db_order.status == "pending":
                db_order.status = "closed"
                db.commit()
            
            return {
                "code": 0,
                "msg": f"订单状态: {trade_status}",
                "data": {
                    "status": trade_status,
                    "trade_status": trade_status
                }
            }
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Query payment error: {error_trace}")
        return {"code": -1, "msg": str(e), "data": None}


@router.post("/alipay/notify")
async def alipay_notify(request: Request, db: Session = Depends(get_db)):
    service = get_alipay_service()
    form_data = await request.form()
    data = dict(form_data)
    
    signature = data.pop("sign")
    
    if service.verify_callback(data, signature):
        trade_status = data.get("trade_status")
        out_trade_no = data.get("out_trade_no")
        
        if trade_status == "TRADE_SUCCESS" or trade_status == "TRADE_FINISHED":
            db_order = db.query(PaymentOrder).filter(PaymentOrder.out_trade_no == out_trade_no).first()
            if db_order and db_order.status == "pending":
                manager = PointsManager(db)
                manager.add_points(db_order.user_id, db_order.points, f"支付宝充值-{out_trade_no}")
                db_order.status = "paid"
                db_order.trade_no = data.get("trade_no")
                db_order.paid_at = datetime.now()
                db.commit()
                print(f"支付成功! 订单号: {out_trade_no}, 用户ID: {db_order.user_id}, 积分: {db_order.points}")
        
        return "success"
    else:
        print("签名验证失败")
        return "fail"


@router.get("/orders")
def get_payment_orders(
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        query = db.query(PaymentOrder).filter(PaymentOrder.user_id == current_user.id)
        total = query.count()
        
        orders = query.order_by(PaymentOrder.created_at.desc())\
            .offset((page - 1) * page_size)\
            .limit(page_size)\
            .all()
        
        order_list = []
        for order in orders:
            order_list.append({
                "id": order.id,
                "out_trade_no": order.out_trade_no,
                "trade_no": order.trade_no,
                "payment_method": order.payment_method,
                "amount": float(order.amount),
                "points": order.points,
                "status": order.status,
                "subject": order.subject,
                "paid_at": order.paid_at.isoformat() if order.paid_at else None,
                "created_at": order.created_at.isoformat()
            })
        
        return {
            "code": 0,
            "msg": "success",
            "data": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "orders": order_list
            }
        }
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Get payment orders error: {error_trace}")
        return {"code": -1, "msg": str(e), "data": None}


@router.post("/confirm")
def confirm_payment(
    request_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    out_trade_no = request_data.get("out_trade_no")
    if not out_trade_no:
        return {"code": -1, "msg": "缺少订单号", "data": None}
    
    try:
        db_order = db.query(PaymentOrder).filter(
            PaymentOrder.out_trade_no == out_trade_no,
            PaymentOrder.user_id == current_user.id
        ).first()
        
        if not db_order:
            return {"code": -1, "msg": "订单不存在", "data": None}
        
        if db_order.status != "pending":
            return {"code": -1, "msg": f"订单状态为 {db_order.status}，无需确认", "data": {"status": db_order.status}}
        
        service = get_alipay_service()
        result = service.query_order(out_trade_no=out_trade_no)
        
        trade_status = result.get("trade_status")
        
        if trade_status == "TRADE_SUCCESS" or trade_status == "TRADE_FINISHED":
            manager = PointsManager(db)
            manager.add_points(db_order.user_id, db_order.points, f"支付宝充值确认-{out_trade_no}")
            db_order.status = "paid"
            db_order.trade_no = result.get("trade_no")
            db_order.paid_at = datetime.now()
            db.commit()
            
            return {
                "code": 0,
                "msg": "确认成功，积分已到账",
                "data": {
                    "status": "paid",
                    "points": db_order.points
                }
            }
        elif trade_status == "WAIT_BUYER_PAY":
            return {
                "code": 0,
                "msg": "订单仍在等待支付中",
                "data": {
                    "status": "pending",
                    "trade_status": trade_status
                }
            }
        elif trade_status == "TRADE_CLOSED":
            db_order.status = "closed"
            db.commit()
            return {
                "code": 0,
                "msg": "订单已关闭",
                "data": {
                    "status": "closed"
                }
            }
        else:
            return {
                "code": 0,
                "msg": f"订单状态: {trade_status}",
                "data": {
                    "status": trade_status
                }
            }
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Confirm payment error: {error_trace}")
        return {"code": -1, "msg": str(e), "data": None}
