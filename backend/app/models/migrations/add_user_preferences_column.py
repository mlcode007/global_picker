#!/usr/bin/env python3
"""为 users 增加 preferences JSON（与 backend/.env 中 MYSQL_* 一致）"""
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
        cur.execute("SHOW COLUMNS FROM users LIKE 'preferences'")
        if not cur.fetchone():
            cur.execute(
                "ALTER TABLE users ADD COLUMN preferences JSON NULL "
                "COMMENT '用户偏好 JSON（如导出列配置）'"
            )
            conn.commit()
            print("已添加 users.preferences")
        else:
            print("users.preferences 已存在")
finally:
    conn.close()
