#!/usr/bin/env python3
"""为 crawl_tasks 增加 status_detail（与 backend/.env 中 MYSQL_* 一致）"""
import os
from pathlib import Path

import pymysql
from dotenv import load_dotenv

# 与 app.config.Settings 相同：读取 backend/.env
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
        cur.execute("SHOW COLUMNS FROM crawl_tasks LIKE 'status_detail'")
        if not cur.fetchone():
            cur.execute(
                "ALTER TABLE crawl_tasks ADD COLUMN status_detail VARCHAR(512) NULL "
                "COMMENT 'running 时进度提示（如验证码）'"
            )
            conn.commit()
            print("已添加 crawl_tasks.status_detail")
        else:
            print("crawl_tasks.status_detail 已存在")
finally:
    conn.close()
