#!/usr/bin/env python3
"""为 discount_codes 增加 duration_months 列（使用后会员有效期，单位：月）。"""
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
        cur.execute("SHOW COLUMNS FROM discount_codes LIKE 'duration_months'")
        if not cur.fetchone():
            cur.execute(
                "ALTER TABLE discount_codes "
                "ADD COLUMN duration_months INT NOT NULL DEFAULT 1 "
                "COMMENT '使用后会员有效期（月）' AFTER price"
            )
            print("已为 discount_codes 添加 duration_months 列")
        else:
            print("discount_codes.duration_months 已存在")

        conn.commit()
finally:
    conn.close()
