import threading
import time
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.payment import PaymentOrder
from app.services.alipay_service import AlipayService
from app.services.points_service import PointsManager

logger = logging.getLogger(__name__)

COMPENSATION_INTERVAL = 60
PENDING_TIMEOUT_MINUTES = 5


def compensate_pending_orders():
    """扫描超时未支付的pending订单，查询支付宝状态并补偿"""
    db = SessionLocal()
    try:
        timeout_threshold = datetime.now() - timedelta(minutes=PENDING_TIMEOUT_MINUTES)
        
        pending_orders = db.query(PaymentOrder).filter(
            PaymentOrder.status == "pending",
            PaymentOrder.created_at <= timeout_threshold
        ).all()
        
        if not pending_orders:
            return
        
        logger.info(f"开始补偿扫描，发现 {len(pending_orders)} 个超时pending订单")
        
        alipay_service = AlipayService()
        
        for order in pending_orders:
            try:
                result = alipay_service.query_order(out_trade_no=order.out_trade_no)
                trade_status = result.get("trade_status")
                
                if trade_status in ("TRADE_SUCCESS", "TRADE_FINISHED"):
                    if order.status == "pending":
                        manager = PointsManager(db)
                        manager.add_points(order.user_id, order.points, f"支付宝充值补偿-{order.out_trade_no}")
                        order.status = "paid"
                        order.trade_no = result.get("trade_no")
                        order.paid_at = datetime.now()
                        db.commit()
                        logger.info(f"补偿成功: 订单 {order.out_trade_no}, 用户 {order.user_id}, 积分 {order.points}")
                
                elif trade_status == "TRADE_CLOSED":
                    order.status = "closed"
                    db.commit()
                    logger.info(f"订单已关闭: {order.out_trade_no}")
                    
            except Exception as e:
                logger.error(f"补偿订单 {order.out_trade_no} 失败: {e}")
                db.rollback()
                
    except Exception as e:
        logger.error(f"补偿扫描异常: {e}")
    finally:
        db.close()


def start_compensation_scheduler():
    """启动后台补偿定时任务"""
    def run_scheduler():
        while True:
            try:
                compensate_pending_orders()
            except Exception as e:
                logger.error(f"补偿定时任务异常: {e}")
            time.sleep(COMPENSATION_INTERVAL)
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info(f"支付补偿定时任务已启动，间隔 {COMPENSATION_INTERVAL} 秒")
