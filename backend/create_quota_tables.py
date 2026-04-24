"""
数据库迁移脚本：创建配额管理相关表
运行方式: cd backend && python3 create_quota_tables.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.database import engine
from app.models.quota import UserQuota, CollectionHistory

def create_tables():
    print("Creating quota tables...")
    UserQuota.__table__.create(engine, checkfirst=True)
    CollectionHistory.__table__.create(engine, checkfirst=True)
    print("Done! Tables created successfully.")

if __name__ == "__main__":
    create_tables()
