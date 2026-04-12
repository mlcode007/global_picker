"""
创建积分系统相关表结构
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from database import SQLALCHEMY_DATABASE_URL


def create_points_tables():
    """创建积分系统相关表结构"""
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    with engine.connect() as conn:
        # 创建用户积分表
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS user_points (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL UNIQUE COMMENT '用户ID',
            points INT NOT NULL DEFAULT 0 COMMENT '当前积分',
            total_earned INT NOT NULL DEFAULT 0 COMMENT '总获取积分',
            total_consumed INT NOT NULL DEFAULT 0 COMMENT '总消耗积分',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """))
        
        # 创建积分交易记录表
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS points_transaction (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL COMMENT '用户ID',
            type ENUM('earn', 'consume') NOT NULL COMMENT '交易类型',
            amount INT NOT NULL COMMENT '积分数量',
            reason TEXT NOT NULL COMMENT '交易原因',
            related_id VARCHAR(128) NULL COMMENT '关联ID',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """))
        
        conn.commit()
        print("积分系统表结构创建成功")


if __name__ == "__main__":
    create_points_tables()