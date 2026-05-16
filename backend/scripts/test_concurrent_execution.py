#!/usr/bin/env python3
"""
测试拍照购并发执行功能
"""
import sys
import time
import threading
from datetime import datetime
sys.path.insert(0, '/Volumes/KIOXIA/SMZDM/MAC01/项目/我的项目/global_picker/backend')

from app.database import SessionLocal
from app.models.product import Product
from app.models.photo_search_task import PhotoSearchTask
from app.workers.pdd_photo.task_scheduler import scheduler, start_scheduler


def create_test_tasks(count=5):
    """创建测试任务"""
    db = SessionLocal()
    task_ids = []
    
    try:
        # 找一个已存在的商品
        product = db.query(Product).first()
        if not product:
            print("❌ 没有找到商品数据")
            return []
        
        for i in range(count):
            task = PhotoSearchTask(
                product_id=product.id,
                status="queued",
                source_image_url=f"https://example.com/test{i}.jpg",
                created_at=datetime.now(),
            )
            db.add(task)
        
        db.commit()
        
        # 获取刚创建的任务
        tasks = db.query(PhotoSearchTask).filter(
            PhotoSearchTask.source_image_url.like("https://example.com/test%")
        ).order_by(PhotoSearchTask.id.desc()).limit(count).all()
        
        task_ids = [t.id for t in tasks]
        print(f"创建了 {len(task_ids)} 个测试任务: {task_ids}")
        
    finally:
        db.close()
    
    return task_ids


def test_concurrent_execution():
    """测试并发执行"""
    print("=== 测试拍照购并发执行 ===")
    
    # 确保调度器运行
    if not scheduler.running:
        scheduler.set_concurrency(2)
        start_scheduler()
        time.sleep(1)
    
    print(f"调度器状态: {'运行中' if scheduler.running else '已停止'}")
    print(f"最大并发数: {scheduler._max_concurrency}")
    
    # 创建测试任务
    task_ids = create_test_tasks(count=4)
    if not task_ids:
        return
    
    # 添加任务到调度队列
    scheduler.add_tasks(task_ids)
    print(f"已添加 {len(task_ids)} 个任务到队列")
    
    # 等待任务调度
    print("\n等待任务调度...")
    for i in range(10):
        status = scheduler.get_queue_status()
        active = status['active_tasks']
        pending = status['pending_tasks']
        print(f"第 {i+1} 秒: 活动任务={active}, 待处理任务={pending}")
        
        if active == 0 and pending == 0:
            print("所有任务已完成")
            break
        
        time.sleep(1)
    
    # 清理测试数据
    db = SessionLocal()
    try:
        deleted = db.query(PhotoSearchTask).filter(
            PhotoSearchTask.source_image_url.like("https://example.com/test%")
        ).delete()
        db.commit()
        print(f"\n清理了 {deleted} 个测试任务")
    finally:
        db.close()


if __name__ == "__main__":
    test_concurrent_execution()