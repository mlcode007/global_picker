"""
Redis 设备锁 —— 分布式锁 + TTL 自动过期 + 心跳续期。

解决并发问题：
1. 多 worker 进程安全抢占设备
2. 任务卡死时锁自动释放（TTL 过期）
3. 正常执行时心跳续期
4. 快速失败，不阻塞
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Optional

import redis

from app.config import get_settings

logger = logging.getLogger(__name__)

# 设备锁 TTL（秒）- 任务执行超时时间
DEVICE_LOCK_TTL = 120
# 心跳续期间隔（秒）
HEARTBEAT_INTERVAL = 30
# 抢锁等待超时（秒）
ACQUIRE_TIMEOUT = 30
# 抢锁轮询间隔（秒）
ACQUIRE_POLL_INTERVAL = 1.0

LOCK_PREFIX = "pdd_photo:device_lock:"
HEARTBEAT_PREFIX = "pdd_photo:device_heartbeat:"


class DeviceLock:
    """Redis 设备锁。"""

    def __init__(self, serial: str):
        self.serial = serial
        self.lock_key = f"{LOCK_PREFIX}{serial}"
        self.heartbeat_key = f"{HEARTBEAT_PREFIX}{serial}"
        self.lock_value = str(uuid.uuid4())
        self._redis: Optional[redis.Redis] = None

    @property
    def redis(self) -> redis.Redis:
        if self._redis is None:
            settings = get_settings()
            self._redis = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
        return self._redis

    def acquire(self, timeout: int = ACQUIRE_TIMEOUT) -> bool:
        """尝试获取设备锁。
        
        Args:
            timeout: 等待超时时间（秒）
            
        Returns:
            是否成功获取锁
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            # SETNX + TTL 原子操作
            acquired = self.redis.set(
                self.lock_key,
                self.lock_value,
                nx=True,
                ex=DEVICE_LOCK_TTL,
            )
            if acquired:
                logger.info("Device %s locked (ttl=%ds)", self.serial, DEVICE_LOCK_TTL)
                return True
            time.sleep(ACQUIRE_POLL_INTERVAL)

        logger.warning("Timeout acquiring device %s lock", self.serial)
        return False

    def release(self) -> bool:
        """释放设备锁（仅释放自己的锁）。"""
        # Lua 脚本：仅当 value 匹配时才删除
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        result = self.redis.eval(script, 1, self.lock_key, self.lock_value)
        if result:
            logger.info("Device %s lock released", self.serial)
        return bool(result)

    def heartbeat(self) -> bool:
        """心跳续期，延长锁 TTL。"""
        # 仅当锁仍存在且是自己的锁时才续期
        current = self.redis.get(self.lock_key)
        if current != self.lock_value:
            logger.warning("Device %s heartbeat failed: lock lost", self.serial)
            return False
        self.redis.expire(self.lock_key, DEVICE_LOCK_TTL)
        self.redis.set(self.heartbeat_key, str(int(time.time())), ex=DEVICE_LOCK_TTL)
        return True

    def is_locked(self) -> bool:
        """检查设备是否被锁定。"""
        return bool(self.redis.exists(self.lock_key))

    def get_lock_owner(self) -> Optional[str]:
        """获取锁的持有者。"""
        return self.redis.get(self.lock_key)

    @classmethod
    def force_release(cls, serial: str) -> bool:
        """强制释放设备锁（管理员操作）。"""
        settings = get_settings()
        r = redis.from_url(settings.redis_url, decode_responses=True)
        lock_key = f"{LOCK_PREFIX}{serial}"
        heartbeat_key = f"{HEARTBEAT_PREFIX}{serial}"
        r.delete(lock_key, heartbeat_key)
        logger.info("Device %s force released", serial)
        return True

    @classmethod
    def get_zombie_locks(cls, max_age_seconds: int = 300) -> list[str]:
        """获取僵尸锁（超过 max_age_seconds 没有心跳的设备）。"""
        settings = get_settings()
        r = redis.from_url(settings.redis_url, decode_responses=True)
        zombies = []
        for key in r.scan_iter(match=f"{HEARTBEAT_PREFIX}*"):
            last_heartbeat = r.get(key)
            if last_heartbeat:
                age = int(time.time()) - int(last_heartbeat)
                if age > max_age_seconds:
                    serial = key.replace(HEARTBEAT_PREFIX, "")
                    zombies.append(serial)
        return zombies
