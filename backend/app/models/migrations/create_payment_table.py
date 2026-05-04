"""
创建支付订单表
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from sqlalchemy import create_engine, text
from app.config import get_settings

settings = get_settings()


def create_payment_table():
    """创建支付订单表"""
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS payment_orders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL COMMENT '用户ID',
            out_trade_no VARCHAR(64) NOT NULL UNIQUE COMMENT '商户订单号',
            trade_no VARCHAR(64) NULL COMMENT '支付宝交易号',
            payment_method VARCHAR(32) NOT NULL DEFAULT 'alipay' COMMENT '支付方式',
            amount DECIMAL(10, 2) NOT NULL COMMENT '支付金额（元）',
            points INT NOT NULL COMMENT '获得积分数量',
            status ENUM('pending', 'paid', 'closed', 'failed') NOT NULL DEFAULT 'pending' COMMENT '订单状态',
            subject VARCHAR(256) NOT NULL COMMENT '订单标题',
            qr_code TEXT NULL COMMENT '二维码内容',
            paid_at DATETIME NULL COMMENT '支付完成时间',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_user_id_status (user_id, status),
            INDEX idx_out_trade_no (out_trade_no),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """))
        
        conn.commit()
        print("支付订单表创建成功")


if __name__ == "__main__":
    create_payment_table()
