#!/usr/bin/env python3
"""
修复卡住的设备和任务脚本

问题分析：
1. 任务完成后设备状态没有被正确更新
2. 调度器可能停止运行

修复步骤：
1. 释放所有状态为 busy 但任务已完成的设备
2. 重启调度器
3. 重新调度所有 queued 任务
"""
import sys
import time
sys.path.insert(0, '/Volumes/KIOXIA/SMZDM/MAC01/项目/我的项目/global_picker/backend')

from app.database import SessionLocal
from app.models.device import Device
from app.models.photo_search_task import PhotoSearchTask
from app.workers.pdd_photo.task_scheduler import scheduler, stop_scheduler, start_scheduler, schedule_tasks


def release_stuck_devices():
    """释放所有卡住的设备（状态为 busy 但任务已完成）"""
    db = SessionLocal()
    released_count = 0
    
    try:
        # 查找所有 busy 状态的设备
        busy_devices = db.query(Device).filter(Device.status == "busy").all()
        
        for device in busy_devices:
            task_id = device.current_task_id
            if task_id:
                # 检查任务状态
                task = db.query(PhotoSearchTask).filter(PhotoSearchTask.id == task_id).first()
                if task:
                    # 如果任务已经完成，释放设备
                    if task.status in ("success", "failed", "cancelled"):
                        print(f"释放设备 {device.device_id}: 任务 #{task_id} 已完成 ({task.status})")
                        device.status = "idle"
                        device.current_task_id = None
                        released_count += 1
                else:
                    # 任务不存在，释放设备
                    print(f"释放设备 {device.device_id}: 任务 #{task_id} 不存在")
                    device.status = "idle"
                    device.current_task_id = None
                    released_count += 1
        
        db.commit()
        print(f"共释放 {released_count} 个卡住的设备")
        
    finally:
        db.close()
    
    return released_count


def restart_scheduler():
    """重启任务调度器"""
    print("重启调度器...")
    
    # 停止现有调度器
    if scheduler.running:
        stop_scheduler()
        time.sleep(1)
    
    # 启动调度器
    start_scheduler()
    time.sleep(1)
    
    if scheduler.running:
        print("调度器重启成功")
    else:
        print("调度器启动失败")
    
    return scheduler.running


def reschedule_queued_tasks():
    """重新调度所有 queued 任务"""
    db = SessionLocal()
    scheduled_count = 0
    
    try:
        queued_tasks = db.query(PhotoSearchTask).filter(PhotoSearchTask.status == "queued").all()
        task_ids = [t.id for t in queued_tasks]
        
        if task_ids:
            print(f"重新调度 {len(task_ids)} 个任务")
            schedule_tasks(task_ids)
            scheduled_count = len(task_ids)
        
    finally:
        db.close()
    
    return scheduled_count


if __name__ == "__main__":
    print("=== 修复卡住的拍照购任务 ===")
    print()
    
    # 步骤1: 释放卡住的设备
    print("步骤1: 释放卡住的设备")
    release_stuck_devices()
    print()
    
    # 步骤2: 重启调度器
    print("步骤2: 重启调度器")
    restart_scheduler()
    print()
    
    # 步骤3: 重新调度任务
    print("步骤3: 重新调度 queued 任务")
    reschedule_queued_tasks()
    print()
    
    print("=== 修复完成 ===")