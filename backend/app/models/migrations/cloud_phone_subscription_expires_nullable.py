#!/usr/bin/env python3
"""云手机订阅 expires_at 改为可空，并按开通时间重算历史数据。"""
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
        cur.execute("SHOW COLUMNS FROM cloud_phone_subscriptions LIKE 'expires_at'")
        col = cur.fetchone()
        if col and col[2] == "NO":
            cur.execute(
                "ALTER TABLE cloud_phone_subscriptions "
                "MODIFY expires_at DATETIME NULL COMMENT '到期时间（未开通空位为 NULL）'"
            )
            print("已修改 cloud_phone_subscriptions.expires_at 为可空")

        # 未绑定空位：expires_at 置 NULL
        cur.execute(
            "UPDATE cloud_phone_subscriptions SET expires_at = NULL "
            "WHERE device_id IS NULL AND status = 'active'"
        )
        print(f"未绑定空位 expires_at 已置 NULL，影响 {cur.rowcount} 行")

        # 已绑定：按 pool.created_at + 30 天重算
        cur.execute(
            """
            UPDATE cloud_phone_subscriptions s
            INNER JOIN cloud_phone_pool p ON s.device_id = p.id
            SET s.expires_at = DATE_ADD(p.created_at, INTERVAL 30 DAY)
            WHERE s.device_id IS NOT NULL AND s.status = 'active'
            """
        )
        print(f"已绑定订阅 expires_at 已重算，影响 {cur.rowcount} 行")

        conn.commit()
finally:
    conn.close()
