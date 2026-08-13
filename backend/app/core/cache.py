"""
企业级 Redis 缓存系统

提供基于 Redis 的缓存层，包含：
- 异步连接池管理
- 单例 RedisClient
- JSON 序列化/反序列化
- 缓存装饰器
- 自动重试机制
- 健康检查
"""

import asyncio
import json
import functools
import hashlib
from typing import (
    Any, Callable, Dict, List, Optional, 
    TypeVar, Union, cast,
)
from datetime import timedelta

import redis.asyncio as aioredis
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import RedisError, TimeoutError, ConnectionError

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("manga.cache")

# ---------------------------------------------------------------------------
# 泛型
# ---------------------------------------------------------------------------
F = TypeVar("F", bound=Callable[..., Any])
T = TypeVar("T")

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

class CacheKeyPrefix:
    """缓存键前缀统一管理。"""
    DEFAULT: str = "manga:"
    USER: str = "manga:user:"
    PROJECT: str = "manga:project:"
    SESSION: str = "manga:session:"
    TASK: str = "manga:task:"
    LLM_RESPONSE: str = "manga:llm:"
    RATE_LIMIT: str = "manga:ratelimit:"

    @classmethod
    def all_prefixes(cls) -> List[str]:
        return [
            v for k, v in vars(cls).items()
            if not k.startswith("_") and isinstance(v, str)
        ]


# ---------------------------------------------------------------------------
# 重试工具
# ---------------------------------------------------------------------------

async def _retry_async(
    coro_factory: Callable[[], Any],
    max_retries: int = 3,
    base_delay: float = 0.1,
    max_delay: float = 2.0,
    backoff: float = 2.0,
    exceptions: tuple = (TimeoutError, ConnectionError, RedisError),
) -> Any:
    """带指数退避的异步重试。"""
    last_exc: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            return await coro_factory()
        except exceptions as e:
            last_exc = e
            if attempt < max_retries:
                delay = min(base_delay * (backoff ** (attempt - 1)), max_delay)
                logger.warning(
                    "Redis 操作重试 [%d/%d]: %s, 等待 %.2fs",
                    attempt, max_retries, e, delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.error("Redis 操作重试耗尽 [%d/%d]: %s", attempt, max_retries, e)
    raise cast(Exception, last_exc)


# ---------------------------------------------------------------------------
# Redis 客户端（单例）
# ---------------------------------------------------------------------------

class RedisClient:
    """Redis 异步客户端（单例模式）。

    用法::

        await RedisClient.get_instance().set("key", {"data": 1})
        value = await RedisClient.get_instance().get("key")
    """

    _instance: Optional["RedisClient"] = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __init__(self) -> None:
        self._pool: Optional[ConnectionPool] = None
        self._redis: Optional[aioredis.Redis] = None
        self._connected: bool = False

    # ---- 单例 ----

    @classmethod
    async def get_instance(cls) -> "RedisClient":
        """获取全局单例实例。"""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    instance = cls()
                    await instance._init_pool()
                    cls._instance = instance
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """重置单例（主要用于测试）。"""
        if cls._instance is not None:
            cls._instance = None

    # ---- 连接池初始化 ----

    async def _init_pool(self) -> None:
        """初始化连接池。"""
        try:
            self._pool = ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=50,
                socket_connect_timeout=5,
                socket_timeout=10,
                socket_keepalive=True,
                retry_on_timeout=True,
                health_check_interval=30,
                decode_responses=True,
            )
            self._redis = aioredis.Redis.from_pool(self._pool)
            await self._redis.ping()
            self._connected = True
            logger.info("Redis 连接池初始化成功: %s", self._safe_redis_url(settings.REDIS_URL))
        except Exception as exc:
            self._connected = False
            logger.warning("Redis 连接失败，缓存降级: %s", exc)

    def _safe_redis_url(self, url: str) -> str:
        """脱敏 Redis URL（隐藏密码）。"""
        if "@" in url:
            parts = url.split("@")
            return f"redis://****@{parts[-1]}"
        return url

    @property
    def client(self) -> aioredis.Redis:
        """获取底层 Redis 客户端实例。"""
        if self._redis is None:
            raise RuntimeError("Redis 客户端未初始化，请先调用 get_instance()")
        return self._redis

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ---- 核心操作方法 ----

    async def get(self, key: str, default: Any = None) -> Any:
        """获取缓存值（自动 JSON 反序列化）。"""
        if not self._connected:
            return default

        async def _do() -> Any:
            raw = await self.client.get(key)
            if raw is None:
                return default
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return raw

        return await _retry_async(_do)

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        nx: bool = False,
    ) -> bool:
        """设置缓存值（自动 JSON 序列化）。

        Args:
            key: 缓存键
            value: 任意可 JSON 序列化的值
            ttl: 过期时间（秒），None 表示永不过期
            nx: 仅当键不存在时设置

        Returns:
            是否设置成功
        """
        if not self._connected:
            return False

        async def _do() -> bool:
            serialized = json.dumps(value, ensure_ascii=False, default=str)
            if ttl is not None:
                return await self.client.set(key, serialized, ex=ttl, nx=nx)
            return await self.client.set(key, serialized, nx=nx)

        return await _retry_async(_do)

    async def delete(self, *keys: str) -> int:
        """删除一个或多个缓存键。"""
        if not self._connected or not keys:
            return 0

        async def _do() -> int:
            return await self.client.delete(*keys)

        return await _retry_async(_do)

    async def exists(self, key: str) -> bool:
        """检查键是否存在。"""
        if not self._connected:
            return False

        async def _do() -> bool:
            return await self.client.exists(key) > 0

        return await _retry_async(_do)

    async def expire(self, key: str, ttl: int) -> bool:
        """设置键的过期时间。"""
        if not self._connected:
            return False

        async def _do() -> bool:
            return await self.client.expire(key, ttl)

        return await _retry_async(_do)

    async def keys(self, pattern: str = "*") -> List[str]:
        """按模式查找键（生产环境慎用）。"""
        if not self._connected:
            return []

        async def _do() -> List[str]:
            return [k async for k in self.client.scan_iter(match=pattern, count=1000)]

        return await _retry_async(_do)

    async def clear_pattern(self, pattern: str) -> int:
        """按模式清除缓存键。

        Args:
            pattern: 键匹配模式，如 ``manga:user:*``

        Returns:
            清除的键数量
        """
        if not self._connected:
            return 0

        async def _do() -> int:
            deleted = 0
            async for key in self.client.scan_iter(match=pattern, count=500):
                await self.client.delete(key)
                deleted += 1
            return deleted

        return await _retry_async(_do)

    async def set_nx(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """仅在键不存在时设置（分布式锁基础）。"""
        return await self.set(key, value, ttl=ttl, nx=True)

    # ---- 批量操作 ----

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """批量获取。"""
        if not self._connected or not keys:
            return {}

        async def _do() -> Dict[str, Any]:
            raw_values = await self.client.mget(*keys)
            result: Dict[str, Any] = {}
            for k, raw in zip(keys, raw_values):
                if raw is None:
                    continue
                try:
                    result[k] = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    result[k] = raw
            return result

        return await _retry_async(_do)

    async def set_many(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """批量设置。"""
        if not self._connected or not mapping:
            return False

        async def _do() -> bool:
            pipe = self.client.pipeline()
            for key, value in mapping.items():
                serialized = json.dumps(value, ensure_ascii=False, default=str)
                if ttl is not None:
                    pipe.set(key, serialized, ex=ttl)
                else:
                    pipe.set(key, serialized)
            await pipe.execute()
            return True

        return await _retry_async(_do)

    # ---- 健康检查 ----

    async def health_check(self) -> Dict[str, Any]:
        """执行完整健康检查。

        Returns:
            dict: 包含连接状态、延迟、内存等信息的字典
        """
        result: Dict[str, Any] = {
            "connected": self._connected,
            "pool_size": 0,
            "active_connections": 0,
            "latency_ms": None,
            "info": {},
        }

        if not self._connected:
            return result

        try:
            # 连接池信息
            if self._pool:
                pool_info = self._pool._connection_kwargs if hasattr(self._pool, "_connection_kwargs") else {}
                result["pool_size"] = self._pool._max_connections if hasattr(self._pool, "_max_connections") else 0

            # 延迟测试
            start = asyncio.get_event_loop().time()
            await self.client.ping()
            latency = (asyncio.get_event_loop().time() - start) * 1000
            result["latency_ms"] = round(latency, 2)

            # 服务器信息
            info = await self.client.info()
            result["info"] = {
                "redis_version": info.get("redis_version", ""),
                "used_memory_human": info.get("used_memory_human", ""),
                "total_connections_received": info.get("total_connections_received", 0),
                "connected_clients": info.get("connected_clients", 0),
                "uptime_in_days": info.get("uptime_in_days", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
            }

            # 命中率
            hits = info.get("keyspace_hits", 0)
            misses = info.get("keyspace_misses", 0)
            total = hits + misses
            if total > 0:
                result["info"]["hit_rate"] = round(hits / total * 100, 2)
            else:
                result["info"]["hit_rate"] = 0.0

        except Exception as exc:
            result["connected"] = False
            result["error"] = str(exc)

        return result

    # ---- 关闭 ----

    async def close(self) -> None:
        """关闭连接池。"""
        if self._redis:
            await self._redis.aclose()
            self._redis = None
        if self._pool:
            await self._pool.aclose()
            self._pool = None
        self._connected = False
        logger.info("Redis 连接池已关闭")


# ---------------------------------------------------------------------------
# 缓存装饰器
# ---------------------------------------------------------------------------

def cached(ttl: int = 300, prefix: Optional[str] = None, key_builder: Optional[Callable[..., str]] = None):
    """函数结果缓存装饰器。

    Args:
        ttl: 缓存过期时间（秒），默认 300
        prefix: 缓存键前缀，默认使用函数名
        key_builder: 自定义键构建函数，接收函数参数并返回完整键名

    用法::

        @cached(ttl=60)
        async def get_user(user_id: int) -> dict:
            ...

        @cached(ttl=300, prefix="manga:llm:")
        async def get_llm_response(prompt: str) -> str:
            ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 构建缓存键
            if key_builder is not None:
                cache_key = key_builder(*args, **kwargs)
            else:
                func_prefix = prefix or f"{CacheKeyPrefix.DEFAULT}{func.__module__}.{func.__qualname__}:"
                # 对参数做哈希，避免键过长
                args_hash = _build_args_hash(*args, **kwargs)
                cache_key = f"{func_prefix}{args_hash}"

            # 尝试获取缓存
            try:
                client = await RedisClient.get_instance()
                cached_value = await client.get(cache_key)
                if cached_value is not None:
                    logger.debug("缓存命中: %s", cache_key)
                    return cached_value
            except Exception as exc:
                logger.warning("缓存读取失败，跳过: %s", exc)

            # 执行原函数
            result = await func(*args, **kwargs)

            # 写入缓存
            try:
                client = await RedisClient.get_instance()
                await client.set(cache_key, result, ttl=ttl)
                logger.debug("缓存写入: %s (ttl=%ds)", cache_key, ttl)
            except Exception as exc:
                logger.warning("缓存写入失败，忽略: %s", exc)

            return result

        return cast(F, wrapper)
    return decorator


def _build_args_hash(*args: Any, **kwargs: Any) -> str:
    """为函数参数构建确定性哈希。"""
    try:
        raw = json.dumps((args, kwargs), sort_keys=True, default=str, ensure_ascii=False)
    except (TypeError, ValueError):
        raw = str((args, kwargs))
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# 便捷函数
# ---------------------------------------------------------------------------

async def get_cached_or_compute(
    key: str,
    compute: Callable[[], Any],
    ttl: int = 300,
) -> Any:
    """获取缓存，未命中则执行 compute 并缓存结果。"""
    client = await RedisClient.get_instance()
    cached = await client.get(key)
    if cached is not None:
        return cached
    result = await compute()
    await client.set(key, result, ttl=ttl)
    return result


async def invalidate_cache(pattern: str) -> int:
    """按模式失效缓存。"""
    client = await RedisClient.get_instance()
    return await client.clear_pattern(pattern)


# ---------------------------------------------------------------------------
# 生命周期管理
# ---------------------------------------------------------------------------

async def init_cache() -> None:
    """应用启动时初始化缓存（在 lifespan 中调用）。"""
    try:
        await RedisClient.get_instance()
    except Exception as exc:
        logger.warning("缓存初始化失败，应用将以无缓存模式运行: %s", exc)


async def close_cache() -> None:
    """应用关闭时释放缓存连接。"""
    try:
        if RedisClient._instance is not None:
            await RedisClient._instance.close()
    except Exception as exc:
        logger.warning("缓存关闭异常: %s", exc)