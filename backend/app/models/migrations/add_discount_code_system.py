#!/usr/bin/env python3
"""创建折扣码表，并为 payment_orders 增加 discount_code 列。"""
import os
from pathlib import Path

import pymysql
from dotenv import load_dotenv

_backend_root = Path(__file__).resolve().parents[3]
load_dotenv(_backend_root / ".env")

conn = pymysql.connect(
    host=os.getenv("MYSQL_HOST", "127.0.0.1"),
    port=int(os.getenv("MYSQL_PORT", "3306")),
    user=os.getenv("MYSQL_USER", "root"),
    password=os.getenv("MYSQL_PASSWORD", ""),
    database=os.getenv("MYSQL_DB", "global_picker"),
    charset="utf8mb4",
)
try:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS discount_codes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                code VARCHAR(64) NOT NULL UNIQUE COMMENT '折扣码',
                tier ENUM('basic', 'pro') NOT NULL COMMENT '适用会员等级',
                price DECIMAL(10,2) NOT NULL COMMENT '使用折扣码后的价格（元/月）',
                is_active TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
                max_uses INT DEFAULT NULL COMMENT '最大可用次数，NULL 表示不限',
                used_count INT NOT NULL DEFAULT 0 COMMENT '已使用次数',
                expires_at DATETIME DEFAULT NULL COMMENT '有效期，NULL 表示长期有效',
                remark VARCHAR(256) DEFAULT NULL COMMENT '备注',
                created_by INT DEFAULT NULL COMMENT '创建管理员ID',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_code (code),
                INDEX idx_tier_active (tier, is_active)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='会员折扣码表'
            """
        )
        print("已创建 discount_codes 表（若不存在）")

        cur.execute("SHOW COLUMNS FROM payment_orders LIKE 'discount_code'")
        if not cur.fetchone():
            cur.execute(
                "ALTER TABLE payment_orders "
                "ADD COLUMN discount_code VARCHAR(64) DEFAULT NULL "
                "COMMENT '使用的折扣码（会员购买时）' AFTER subject"
            )
            print("已为 payment_orders 添加 discount_code 列")
        else:
            print("payment_orders.discount_code 已存在")

        conn.commit()
finally:
    conn.close()
