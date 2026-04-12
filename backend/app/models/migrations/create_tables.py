#!/usr/bin/env python3
"""
自动创建数据库表
"""
import logging
from app.database import engine, Base

# 导入所有需要创建的模型
from app.models.user import User
from app.models.product import Product
from app.models.crawl_task import CrawlTask
from app.models.pdd_match import PddMatch
from app.models.profit_record import ProfitRecord
from app.models.device import Device
from app.models.photo_search_task import PhotoSearchTask, DeviceActionLog
from app.models.points import UserPoints, PointsTransaction

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

def create_tables():
    """创建数据库表"""
    try:
        logger.info("开始创建数据库表...")
        # Base.metadata.drop_all(engine)  # 注意：这会删除所有表，谨慎使用
        Base.metadata.create_all(engine)
        logger.info("数据库表创建成功！")
    except Exception as e:
        logger.error(f"创建数据库表失败: {e}")
        raise

if __name__ == "__main__":
    create_tables()