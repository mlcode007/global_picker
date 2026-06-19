#!/usr/bin/env python3
"""为 user_crawl_configs 增加 region_proxies JSON 列（按 TikTok 国家配置不同代理）"""
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
        cur.execute("SHOW COLUMNS FROM user_crawl_configs LIKE 'region_proxies'")
        if not cur.fetchone():
            cur.execute(
                "ALTER TABLE user_crawl_configs ADD COLUMN region_proxies JSON NULL "
                "COMMENT '分国家代理配置，key 为 region code（PH/MY/TH/SG/ID/VN...）'"
            )
            conn.commit()
            print("已添加 user_crawl_configs.region_proxies")
        else:
            print("user_crawl_configs.region_proxies 已存在")
finally:
    conn.close()
