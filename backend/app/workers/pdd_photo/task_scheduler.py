"""
拍照购任务调度器 —— 支持多设备并行处理的任务调度中心。

核心功能：
1. 管理任务队列（支持优先级）
2. 智能分配设备（根据设备可用性）
3. 控制并发度（可配置最大并行数）
4. 自动重试失败任务
5. 监控任务状态
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import deque
from typing import Dict, List, Optional, Set

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.photo_search_task import PhotoSearchTask
from app.models.device import Device
from app.services import photo_search_service
from .device_manager import DeviceManager
from .worker import execute_photo_search_task

logger = logging.getLogger(__name__)

# 默认并发度（使用所有可用设备）
DEFAULT_CONCURRENCY = None

# 调度间隔（秒）
SCHEDULE_INTERVAL = 1.0

# 任务优先级
PRIORITY_HIGH = 1
PRIORITY_NORMAL = 2
PRIORITY_LOW = 3


class TaskScheduler:
    """任务调度器 - 管理多设备并行拍照购任务"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._initialized = True
        self._running = False
        self._scheduler_thread = None
        self._max_concurrency = DEFAULT_CONCURRENCY
        self._active_tasks: Set[int] = set()
        self._task_lock = threading.Lock()
        self._condition = threading.Condition()
        self._pending_tasks: Dict[int, deque] = {
            PRIORITY_HIGH: deque(),
            PRIORITY_NORMAL: deque(),
            PRIORITY_LOW: deque(),
        }

    @property
    def running(self) -> bool:
        return self._running

    @property
    def active_task_count(self) -> int:
        with self._task_lock:
            return len(self._active_tasks)

    def set_concurrency(self, max_concurrent: Optional[int]) -> None:
        """设置最大并发数"""
        self._max_concurrency = max_concurrent
        logger.info("Task scheduler concurrency set to %s", max_concurrent)

    def _get_max_concurrent_tasks(self, db: Session) -> int:
        """获取当前允许的最大并发任务数"""
        if self._max_concurrency is not None:
            return self._max_concurrency
        # 默认使用所有可用设备数
        mgr = DeviceManager(db)
        return mgr.get_idle_count() or 1

    def _get_available_slots(self, db: Session) -> int:
        """获取当前可用的任务槽位数量"""
        max_tasks = self._get_max_concurrent_tasks(db)
        active_count = self.active_task_count
        return max(0, max_tasks - active_count)

    def add_task(self, task_id: int, priority: int = PRIORITY_NORMAL) -> None:
        """添加任务到调度队列"""
        with self._condition:
            if priority not in self._pending_tasks:
                priority = PRIORITY_NORMAL
            self._pending_tasks[priority].append(task_id)
            self._condition.notify()
        logger.debug("Task #%d added to queue with priority %d", task_id, priority)

    def add_tasks(self, task_ids: List[int], priority: int = PRIORITY_NORMAL) -> None:
        """批量添加任务到调度队列"""
        with self._condition:
            if priority not in self._pending_tasks:
                priority = PRIORITY_NORMAL
            self._pending_tasks[priority].extend(task_ids)
            self._condition.notify()
        logger.debug("Added %d tasks to queue with priority %d", len(task_ids), priority)

    def _get_next_task(self) -> Optional[int]:
        """获取下一个待执行的任务（按优先级）"""
        with self._condition:
            for priority in [PRIORITY_HIGH, PRIORITY_NORMAL, PRIORITY_LOW]:
                if self._pending_tasks[priority]:
                    return self._pending_tasks[priority].popleft()
            return None

    def _mark_task_started(self, task_id: int) -> bool:
        """标记任务开始执行"""
        with self._task_lock:
            if task_id in self._active_tasks:
                return False
            self._active_tasks.add(task_id)
            return True

    def _mark_task_completed(self, task_id: int) -> None:
        """标记任务完成"""
        with self._task_lock:
            self._active_tasks.discard(task_id)
        with self._condition:
            self._condition.notify()

    def _execute_task(self, task_id: int) -> None:
        """执行单个拍照购任务"""
        try:
            if not self._mark_task_started(task_id):
                logger.warning("Task #%d already running, skipping", task_id)
                return

            logger.info("Scheduling task #%d for execution", task_id)
            execute_photo_search_task(task_id)
        finally:
            self._mark_task_completed(task_id)

    def _schedule_loop(self) -> None:
        """调度主循环"""
        logger.info("Task scheduler started")

        consecutive_errors = 0
        max_consecutive_errors = 10

        while self._running:
            try:
                db = SessionLocal()
                try:
                    available_slots = self._get_available_slots(db)
                    logger.debug("Scheduler loop: available_slots=%d, active_tasks=%d", 
                                available_slots, self.active_task_count)

                    if available_slots > 0:
                        # 尝试从队列获取任务
                        for _ in range(available_slots):
                            task_id = self._get_next_task()
                            if task_id is None:
                                break

                            # 验证任务状态
                            task = photo_search_service.get_task(db, task_id)
                            if not task or task.status != "queued":
                                logger.debug("Task #%d not in queued state, skipping", task_id)
                                continue

                            # 提交到后台线程执行
                            thread = threading.Thread(
                                target=self._execute_task,
                                args=(task_id,),
                                daemon=True,
                                name=f"PhotoSearchTask-{task_id}"
                            )
                            thread.start()
                            logger.info("Task #%d scheduled for execution", task_id)

                    # 检查并加载数据库中的 queued 任务
                    loaded_count = self._load_queued_tasks(db)
                    if loaded_count > 0:
                        logger.info("Loaded %d queued tasks from database", loaded_count)

                    consecutive_errors = 0

                finally:
                    db.close()

            except Exception as e:
                consecutive_errors += 1
                logger.exception("Scheduler loop error (count=%d): %s", consecutive_errors, e)
                
                # 如果连续错误太多，暂停一下避免无限循环
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("Too many consecutive errors, pausing for 10 seconds")
                    time.sleep(10)
                    consecutive_errors = 0

            # 等待下一次调度
            with self._condition:
                self._condition.wait(SCHEDULE_INTERVAL)

        logger.info("Task scheduler stopped")

    def _load_queued_tasks(self, db: Session) -> int:
        """从数据库加载 queued 状态的任务到内存队列"""
        try:
            queued_tasks = db.query(PhotoSearchTask).filter(
                PhotoSearchTask.status == "queued"
            ).order_by(
                PhotoSearchTask.created_at.asc()
            ).limit(100).all()

            loaded_count = 0
            with self._condition:
                # 获取当前活跃任务的快照
                active_ids = set(self._active_tasks)
                
                for task in queued_tasks:
                    if task.id in active_ids:
                        continue
                    
                    # 检查是否已在队列中（使用集合进行快速查找）
                    already_in_queue = False
                    for queue in self._pending_tasks.values():
                        if task.id in queue:
                            already_in_queue = True
                            break
                    
                    if not already_in_queue:
                        self._pending_tasks[PRIORITY_NORMAL].append(task.id)
                        loaded_count += 1

            return loaded_count
        except Exception as e:
            logger.exception("Error loading queued tasks: %s", e)
            return 0

    def start(self) -> None:
        """启动调度器"""
        if self._running:
            logger.warning("Task scheduler already running")
            return

        self._running = True
        self._scheduler_thread = threading.Thread(
            target=self._schedule_loop,
            daemon=True,
            name="TaskScheduler"
        )
        self._scheduler_thread.start()
        logger.info("Task scheduler starting...")
        logger.info("Scheduler thread started: %s", self._scheduler_thread.ident)

    def stop(self) -> None:
        """停止调度器"""
        self._running = False
        with self._condition:
            self._condition.notify_all()

        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
            self._scheduler_thread = None

    def get_queue_status(self) -> dict:
        """获取队列状态"""
        with self._condition:
            total_pending = sum(len(q) for q in self._pending_tasks.values())
        return {
            'active_tasks': self.active_task_count,
            'pending_tasks': total_pending,
            'pending_by_priority': {
                'high': len(self._pending_tasks[PRIORITY_HIGH]),
                'normal': len(self._pending_tasks[PRIORITY_NORMAL]),
                'low': len(self._pending_tasks[PRIORITY_LOW]),
            },
        }


class BatchTaskManager:
    """批量任务管理器"""

    def __init__(self):
        self._batch_tasks: Dict[str, dict] = {}
        self._lock = threading.Lock()

    def create_batch(self, product_ids: List[int], user_id: int = None) -> str:
        """创建批量任务"""
        batch_id = f"batch_{uuid.uuid4().hex[:8]}"
        with self._lock:
            self._batch_tasks[batch_id] = {
                'product_ids': list(product_ids),
                'user_id': user_id,
                'task_ids': [],
                'created_at': time.time(),
                'completed_at': None,
            }
        return batch_id

    def add_task_to_batch(self, batch_id: str, task_id: int) -> bool:
        """将任务添加到批次"""
        with self._lock:
            if batch_id not in self._batch_tasks:
                return False
            self._batch_tasks[batch_id]['task_ids'].append(task_id)
            return True

    def get_batch_info(self, batch_id: str) -> Optional[dict]:
        """获取批次信息"""
        with self._lock:
            return self._batch_tasks.get(batch_id)

    def mark_batch_completed(self, batch_id: str) -> bool:
        """标记批次完成"""
        with self._lock:
            if batch_id not in self._batch_tasks:
                return False
            self._batch_tasks[batch_id]['completed_at'] = time.time()
            return True

    def cleanup_old_batches(self, max_age_hours: int = 24) -> int:
        """清理过期批次"""
        now = time.time()
        expired = []
        with self._lock:
            for batch_id, info in self._batch_tasks.items():
                age_hours = (now - info['created_at']) / 3600
                if age_hours > max_age_hours:
                    expired.append(batch_id)
            for batch_id in expired:
                del self._batch_tasks[batch_id]
        return len(expired)


# 全局调度器实例
scheduler = TaskScheduler()
batch_manager = BatchTaskManager()


def start_scheduler():
    """启动任务调度器"""
    scheduler.start()


def stop_scheduler():
    """停止任务调度器"""
    scheduler.stop()


def schedule_task(task_id: int, priority: int = PRIORITY_NORMAL):
    """调度单个任务"""
    scheduler.add_task(task_id, priority)


def schedule_tasks(task_ids: List[int], priority: int = PRIORITY_NORMAL):
    """调度多个任务"""
    scheduler.add_tasks(task_ids, priority)


def set_scheduler_concurrency(max_concurrent: Optional[int]):
    """设置调度器并发度"""
    scheduler.set_concurrency(max_concurrent)