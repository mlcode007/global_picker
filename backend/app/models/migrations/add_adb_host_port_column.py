#!/usr/bin/env python3
"""
为 cloud_phone_pool 表添加 adb_host_port 字段
"""
import mysql.connector
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 数据库连接信息
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', 3306))
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '123456')
DB_NAME = os.getenv('DB_NAME', 'global_picker')

try:
    # 连接数据库
    conn = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cursor = conn.cursor()
    
    # 检查字段是否已存在
    cursor.execute("SHOW COLUMNS FROM cloud_phone_pool LIKE 'adb_host_port'")
    result = cursor.fetchone()
    
    if not result:
        # 添加 adb_host_port 字段
        cursor.execute("ALTER TABLE cloud_phone_pool ADD COLUMN adb_host_port VARCHAR(64) NULL COMMENT 'ADB连接端口'")
        conn.commit()
        print("成功添加 adb_host_port 字段")
    else:
        print("adb_host_port 字段已存在")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"添加字段失败: {e}")
