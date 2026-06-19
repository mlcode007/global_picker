#!/usr/bin/env python3
"""为 discount_codes 增加 status 列（一次性折扣码：unused/used）。"""
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
        cur.execute("SHOW COLUMNS FROM discount_codes LIKE 'status'")
        if not cur.fetchone():
            cur.execute(
                "ALTER TABLE discount_codes "
                "ADD COLUMN status ENUM('unused','used') NOT NULL DEFAULT 'unused' "
                "COMMENT '使用状态：未使用/已使用（一次性）' AFTER is_active"
            )
            print("已为 discount_codes 添加 status 列")
        else:
            print("discount_codes.status 已存在")

        # 历史数据：已使用过的折扣码标记为 used
        cur.execute("UPDATE discount_codes SET status='used' WHERE used_count > 0")
        print(f"已将 {cur.rowcount} 条已用折扣码标记为 used")

        conn.commit()
finally:
    conn.close()
