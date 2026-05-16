#!/usr/bin/env python3
"""
测试设备超时检测和自动释放功能
"""
import sys
import time
from datetime import datetime, timedelta
sys.path.insert(0, '/Volumes/KIOXIA/SMZDM/MAC01/项目/我的项目/global_picker/backend')

from app.database import SessionLocal
from app.models.device import Device
from app.models.photo_search_task import PhotoSearchTask
from app.workers.pdd_photo.device_manager import DeviceManager, TASK_TIMEOUT_MINUTES


def test_timeout_detection():
    """测试超时检测功能"""
    db = SessionLocal()
    
    try:
        # 创建一个超时的任务（使用已有的商品）
        past_time = datetime.now() - timedelta(minutes=TASK_TIMEOUT_MINUTES + 2)
        
        # 找一个已存在的商品来创建任务
        from app.models.product import Product
        product = db.query(Product).first()
        if not product:
            print("❌ 没有找到商品数据，请先创建商品")
            return
        
        # 创建一个超时的任务
        task = PhotoSearchTask(
            product_id=product.id,
            status="running",
            source_image_url="https://example.com/test.jpg",
            started_at=past_time,
            created_at=past_time,
        )
        db.add(task)
        db.commit()
        
        # 创建一个 busy 状态的设备
        device = Device(
            device_id="test-device:1000",
            device_name="Test Device",
            device_type="cloud_phone",
            status="busy",
            current_task_id=task.id,
            last_heartbeat=past_time,
        )
        db.add(device)
        db.commit()
        
        print(f"创建测试数据:")
        print(f"  商品ID: {product.id}")
        print(f"  任务ID: {task.id} (started_at: {task.started_at})")
        print(f"  设备: {device.device_id} (status: {device.status})")
        
        # 检查初始状态
        print(f"\n初始设备状态: {device.status}")
        assert device.status == "busy", "设备应该是 busy 状态"
        
        # 创建设备管理器并检测超时设备
        mgr = DeviceManager(db)
        released = mgr._check_and_release_timeout_devices()
        
        print(f"释放的设备数量: {released}")
        assert released == 1, f"应该释放 1 个设备，实际释放 {released} 个"
        
        # 检查设备状态是否变为 idle
        db.refresh(device)
        print(f"释放后设备状态: {device.status}")
        assert device.status == "idle", "设备应该被释放为 idle 状态"
        assert device.current_task_id is None, "设备应该没有绑定任务"
        
        print("\n✅ 测试通过！超时设备已被正确释放")
        
    finally:
        # 清理测试数据
        db.query(Device).filter(Device.device_id == "test-device:1000").delete()
        db.query(PhotoSearchTask).filter(PhotoSearchTask.source_image_url == "https://example.com/test.jpg").delete()
        db.commit()
        db.close()


if __name__ == "__main__":
    print(f"=== 测试设备超时检测功能 ===")
    print(f"超时阈值: {TASK_TIMEOUT_MINUTES} 分钟")
    test_timeout_detection()