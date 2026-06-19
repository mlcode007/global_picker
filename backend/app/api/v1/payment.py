import traceback
import uuid
import re
from typing import Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.payment import PaymentOrder
from app.models.cloud_phone_subscription import CloudPhoneSubscription
from app.core.security import get_current_user
from app.core.membership import MEMBERSHIP_PRICES, CLOUD_PHONE_PRICE, CLOUD_PHONE_MAX, CLOUD_PHONE_PERIOD_DAYS
from app.services.alipay_service import AlipayService
from app.services.points_service import PointsManager
from app.services.discount_service import validate_discount_code, consume_discount_code, DiscountCodeError

router = APIRouter(prefix="/payment", tags=["payment"])
alipay_service = None


def get_alipay_service():
    global alipay_service
    if alipay_service is None:
        alipay_service = AlipayService()
    return alipay_service


def _cloud_phone_order_quantity(order: PaymentOrder) -> int:
    """从订单标题解析云手机购买数量，如「云手机订阅-2台」。"""
    match = re.search(r"云手机订阅-(\d+)台", order.subject or "")
    if match:
        return max(1, int(match.group(1)))
    return 1


def _is_cloud_phone_renew_order(order: PaymentOrder) -> bool:
    return (order.subject or "").startswith("云手机续费-")


def _count_valid_cloud_phone_subscriptions(db: Session, user_id: int) -> int:
    """有效订阅数（含空位与未到期已开通）。"""
    from sqlalchemy import func, or_
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return db.query(func.count(CloudPhoneSubscription.id)).filter(
        CloudPhoneSubscription.user_id == user_id,
        CloudPhoneSubscription.status == "active",
        or_(
            CloudPhoneSubscription.expires_at.is_(None),
            CloudPhoneSubscription.expires_at > now,
        ),
    ).scalar() or 0


def _fulfill_cloud_phone_renew(db: Session, order: PaymentOrder) -> None:
    phone_id = (order.subject or "").replace("云手机续费-", "", 1)
    from app.models.cloud_phone import CloudPhonePool

    pool = db.query(CloudPhonePool).filter(
        CloudPhonePool.phone_id == phone_id,
        CloudPhonePool.created_by == order.user_id,
    ).first()
    if not pool:
        raise ValueError(f"续费设备不存在: {phone_id}")

    sub = db.query(CloudPhoneSubscription).filter(
        CloudPhoneSubscription.device_id == pool.id,
        CloudPhoneSubscription.user_id == order.user_id,
        CloudPhoneSubscription.status == "active",
    ).first()
    if not sub or not sub.expires_at:
        raise ValueError(f"设备 {phone_id} 无有效订阅")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    base = sub.expires_at if sub.expires_at > now else now
    sub.expires_at = base + timedelta(days=CLOUD_PHONE_PERIOD_DAYS)


def _fulfill_order(db: Session, order: PaymentOrder):
    """根据订单类型执行对应的履约逻辑"""
    if order.order_type == "points":
        manager = PointsManager(db)
        manager.add_points(order.user_id, order.points, f"支付宝充值-{order.out_trade_no}")

    elif order.order_type == "membership":
        tier = order.subject.split("-")[-1].strip()  # subject: "会员购买-基础版"
        tier_map = {"基础版": "basic", "专业版": "pro"}
        tier_key = tier_map.get(tier, "free")

        user = db.query(User).filter(User.id == order.user_id).first()
        if user:
            user.membership_tier = tier_key
            # 会员有效期1个月，如果当前未过期则在当前到期时间上续费
            now = datetime.now(timezone.utc)
            base = user.membership_expires_at.replace(tzinfo=timezone.utc) if user.membership_expires_at and user.membership_expires_at.replace(tzinfo=timezone.utc) > now else now
            user.membership_expires_at = base + timedelta(days=30)

        # 使用了折扣码则计数 +1
        if getattr(order, "discount_code", None):
            consume_discount_code(db, order.discount_code)

    elif order.order_type == "cloud_phone":
        if _is_cloud_phone_renew_order(order):
            _fulfill_cloud_phone_renew(db, order)
        else:
            quantity = _cloud_phone_order_quantity(order)
            for _ in range(quantity):
                db.add(CloudPhoneSubscription(
                    user_id=order.user_id,
                    order_id=order.id,
                    status="active",
                    expires_at=None,
                ))


class CreatePaymentRequest(BaseModel):
    points: int


class CreateMembershipPaymentRequest(BaseModel):
    tier: str  # "basic" or "pro"
    discount_code: Optional[str] = None  # 可选折扣码


class CreateCloudPhonePaymentRequest(BaseModel):
    quantity: int = 1  # 购买几台


class RenewCloudPhonePaymentRequest(BaseModel):
    phone_id: str


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
            order_type="points",
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


@router.post("/alipay/membership")
def create_membership_payment(
    request: CreateMembershipPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """购买会员"""
    if request.tier not in ("basic", "pro"):
        raise HTTPException(status_code=400, detail="无效的会员等级，仅支持 basic 或 pro")

    tier_name = {"basic": "基础版", "pro": "专业版"}[request.tier]
    amount = float(MEMBERSHIP_PRICES[request.tier])

    # 折扣码：校验通过则使用折扣价
    applied_code = None
    code = (request.discount_code or "").strip()
    if code:
        try:
            discount = validate_discount_code(db, code, request.tier)
        except DiscountCodeError as e:
            raise HTTPException(status_code=400, detail=str(e))
        amount = float(discount.price)
        applied_code = discount.code

    out_trade_no = f"GM{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8]}"
    subject = f"会员购买-{tier_name}"

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
            order_type="membership",
            amount=amount,
            points=0,
            status='pending',
            subject=subject,
            discount_code=applied_code,
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
                "tier": request.tier,
                "discount_code": applied_code,
            }
        }
    except Exception as e:
        db.rollback()
        error_trace = traceback.format_exc()
        print(f"Membership payment error: {error_trace}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alipay/cloud-phone")
def create_cloud_phone_payment(
    request: CreateCloudPhonePaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """购买云手机订阅（新购空位，开通时才起算 30 天）"""
    if request.quantity < 1 or request.quantity > CLOUD_PHONE_MAX:
        raise HTTPException(status_code=400, detail=f"购买数量需在1-{CLOUD_PHONE_MAX}之间")

    active_count = _count_valid_cloud_phone_subscriptions(db, current_user.id)

    if active_count + request.quantity > CLOUD_PHONE_MAX:
        raise HTTPException(status_code=400, detail=f"已有{active_count}台订阅，最多{CLOUD_PHONE_MAX}台")

    amount = float(CLOUD_PHONE_PRICE * request.quantity)
    out_trade_no = f"GC{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8]}"
    subject = f"云手机订阅-{request.quantity}台"

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
            order_type="cloud_phone",
            amount=amount,
            points=0,
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
                "quantity": request.quantity,
            }
        }
    except Exception as e:
        db.rollback()
        error_trace = traceback.format_exc()
        print(f"Cloud phone payment error: {error_trace}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alipay/cloud-phone/renew")
def create_cloud_phone_renew_payment(
    request: RenewCloudPhonePaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """续费已开通云手机（未到期才允许，延长 expires_at +30 天）。"""
    from app.models.cloud_phone import CloudPhonePool

    phone_id = (request.phone_id or "").strip()
    if not phone_id:
        raise HTTPException(status_code=400, detail="请指定云手机 ID")

    pool = db.query(CloudPhonePool).filter(
        CloudPhonePool.phone_id == phone_id,
        CloudPhonePool.created_by == current_user.id,
    ).first()
    if not pool:
        raise HTTPException(status_code=404, detail="设备不存在或不属于当前用户")

    sub = db.query(CloudPhoneSubscription).filter(
        CloudPhoneSubscription.device_id == pool.id,
        CloudPhoneSubscription.user_id == current_user.id,
        CloudPhoneSubscription.status == "active",
    ).first()
    if not sub or not sub.expires_at:
        raise HTTPException(status_code=400, detail="该设备无有效订阅，请重新购买")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if sub.expires_at <= now:
        raise HTTPException(status_code=400, detail="设备已到期，请重新购买并开通")

    amount = float(CLOUD_PHONE_PRICE)
    out_trade_no = f"GR{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8]}"
    subject = f"云手机续费-{phone_id}"

    try:
        service = get_alipay_service()
        qr_code = service.create_qr_code_url(
            out_trade_no=out_trade_no,
            total_amount=str(amount),
            subject=subject,
        )

        db_order = PaymentOrder(
            user_id=current_user.id,
            out_trade_no=out_trade_no,
            payment_method="alipay",
            order_type="cloud_phone",
            amount=amount,
            points=0,
            status="pending",
            subject=subject,
            qr_code=qr_code,
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
                "phone_id": phone_id,
            },
        }
    except Exception as e:
        db.rollback()
        error_trace = traceback.format_exc()
        print(f"Cloud phone renew payment error: {error_trace}")
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
                _fulfill_order(db, db_order)
                db_order.status = "paid"
                db_order.trade_no = result.get("trade_no")
                db_order.paid_at = datetime.now()
                db.commit()
            
            return {
                "code": 0,
                "msg": "支付成功",
                "data": {
                    "status": "paid",
                    "trade_status": trade_status,
                    "order_type": db_order.order_type if db_order else None,
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
                _fulfill_order(db, db_order)
                db_order.status = "paid"
                db_order.trade_no = data.get("trade_no")
                db_order.paid_at = datetime.now()
                db.commit()
                print(f"支付成功! 订单号: {out_trade_no}, 用户ID: {db_order.user_id}, 类型: {db_order.order_type}")
        
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
                "order_type": order.order_type,
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
            _fulfill_order(db, db_order)
            db_order.status = "paid"
            db_order.trade_no = result.get("trade_no")
            db_order.paid_at = datetime.now()
            db.commit()
            
            return {
                "code": 0,
                "msg": "确认成功",
                "data": {
                    "status": "paid",
                    "order_type": db_order.order_type,
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
