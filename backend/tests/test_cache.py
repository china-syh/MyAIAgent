"""
缓存系统测试

测试 RedisClient 的核心操作和缓存装饰器。
使用 unittest.mock 模拟 Redis，避免依赖实际 Redis 服务。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import uuid

from app.core.cache import (
    RedisClient,
    cached,
    CacheKeyPrefix,
    invalidate_cache,
    get_cached_or_compute,
)


@pytest.fixture(autouse=True)
def reset_redis_singleton():
    """每个测试前重置 RedisClient 单例。"""
    RedisClient.reset_instance()
    yield
    RedisClient.reset_instance()


class TestCacheOperations:
    """缓存核心操作测试。"""

    @pytest.mark.asyncio
    async def test_cache_set_get(self):
        """缓存设置和获取 - 应正确存储和返回数据。"""
        # 手动模拟 RedisClient
        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps({"key": "value"})
        mock_redis.set.return_value = True

        with patch.object(RedisClient, '_init_pool', new=AsyncMock()):
            with patch.object(RedisClient, 'client', new=mock_redis):
                with patch.object(RedisClient, '_connected', True, create=True):
                    instance = RedisClient()
                    instance._redis = mock_redis
                    instance._connected = True
                    RedisClient._instance = instance

                    # 测试 set
                    result = await instance.set("test_key", {"key": "value"}, ttl=60)
                    assert result is True

                    # 测试 get
                    value = await instance.get("test_key")
                    assert value == {"key": "value"}

    @pytest.mark.asyncio
    async def test_cache_get_default(self):
        """缓存获取不存在的键 - 应返回默认值。"""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None

        with patch.object(RedisClient, '_init_pool', new=AsyncMock()):
            instance = RedisClient()
            instance._redis = mock_redis
            instance._connected = True
            RedisClient._instance = instance

            value = await instance.get("nonexistent_key", default="default_value")
            assert value == "default_value"

    @pytest.mark.asyncio
    async def test_cache_delete(self):
        """缓存删除 - 应正确删除并返回删除数量。"""
        mock_redis = AsyncMock()
        mock_redis.delete.return_value = 1

        with patch.object(RedisClient, '_init_pool', new=AsyncMock()):
            instance = RedisClient()
            instance._redis = mock_redis
            instance._connected = True
            RedisClient._instance = instance

            result = await instance.delete("test_key")
            assert result == 1

    @pytest.mark.asyncio
    async def test_cache_delete_multiple(self):
        """批量删除 - 应正确删除多个键。"""
        mock_redis = AsyncMock()
        mock_redis.delete.return_value = 3

        with patch.object(RedisClient, '_init_pool', new=AsyncMock()):
            instance = RedisClient()
            instance._redis = mock_redis
            instance._connected = True
            RedisClient._instance = instance

            result = await instance.delete("key1", "key2", "key3")
            assert result == 3

    @pytest.mark.asyncio
    async def test_cache_ttl(self):
        """缓存过期 - 模拟 TTL 过期后返回默认值。"""
        mock_redis = AsyncMock()
        # 第一次调用返回数据，第二次返回 None（模拟过期）
        mock_redis.get.side_effect = [
            json.dumps({"data": "cached"}),
            None,
        ]

        with patch.object(RedisClient, '_init_pool', new=AsyncMock()):
            instance = RedisClient()
            instance._redis = mock_redis
            instance._connected = True
            RedisClient._instance = instance

            # 第一次获取 - 缓存命中
            value = await instance.get("ttl_key")
            assert value == {"data": "cached"}

            # 重置 mock 模拟过期
            mock_redis.get.return_value = None

            # 第二次获取 - 缓存未命中
            value = await instance.get("ttl_key", default="expired")
            assert value == "expired"

    @pytest.mark.asyncio
    async def test_cache_exists(self):
        """缓存存在检查 - 应正确返回布尔值。"""
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = 1

        with patch.object(RedisClient, '_init_pool', new=AsyncMock()):
            instance = RedisClient()
            instance._redis = mock_redis
            instance._connected = True
            RedisClient._instance = instance

            exists = await instance.exists("existing_key")
            assert exists is True

            mock_redis.exists.return_value = 0
            exists = await instance.exists("nonexistent_key")
            assert exists is False

    @pytest.mark.asyncio
    async def test_cache_not_connected(self):
        """缓存未连接 - 应优雅降级返回默认值。"""
        instance = RedisClient()
        instance._connected = False
        RedisClient._instance = instance

        # 不抛出异常，返回默认值
        value = await instance.get("any_key", default="fallback")
        assert value == "fallback"

        result = await instance.set("any_key", "value")
        assert result is False

        deleted = await instance.delete("any_key")
        assert deleted == 0


class TestCacheDecorator:
    """缓存装饰器测试。"""

    @pytest.mark.asyncio
    async def test_cached_decorator(self):
        """缓存装饰器 - 应缓存函数结果。"""
        mock_redis = AsyncMock()
        # 第一次 miss，第二次 hit
        mock_redis.get.side_effect = [None, json.dumps("cached_result")]
        mock_redis.set.return_value = True

        call_count = 0

        async def compute_func(param: str) -> str:
            nonlocal call_count
            call_count += 1
            return f"result_{param}"

        with patch.object(RedisClient, 'get_instance', new=AsyncMock(return_value=MagicMock(
            get=mock_redis.get,
            set=mock_redis.set,
        ))):
            # 此时 RedisClient.get_instance 返回的是 MagicMock，不是真正的 RedisClient
            # 我们需要更精确的 mock
            pass

        # 更精确的测试：直接测试装饰器逻辑
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=None)
        mock_client.set = AsyncMock(return_value=True)

        with patch.object(RedisClient, 'get_instance', new=AsyncMock(return_value=mock_client)):
            decorated = cached(ttl=60)(compute_func)

            # 第一次调用 - 缓存未命中，执行原函数
            result = await decorated("test")
            assert result == "result_test"
            assert call_count == 1
            mock_client.set.assert_called_once()

            # 重置 mock 模拟第二次调用命中缓存
            mock_client.get = AsyncMock(return_value="result_test")
            mock_client.set = AsyncMock(return_value=True)

            result = await decorated("test")
            assert result == "result_test"
            # 未调用 set，因为缓存命中
            # call_count 仍为 1，因为未执行原函数
            assert call_count == 1

    @pytest.mark.asyncio
    async def test_cached_decorator_with_different_args(self):
        """缓存装饰器 - 不同参数应生成不同缓存键。"""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=None)
        mock_client.set = AsyncMock(return_value=True)

        call_count = 0

        async def compute(a: int, b: int) -> int:
            nonlocal call_count
            call_count += 1
            return a + b

        with patch.object(RedisClient, 'get_instance', new=AsyncMock(return_value=mock_client)):
            decorated = cached(ttl=60)(compute)

            result1 = await decorated(1, 2)
            result2 = await decorated(3, 4)

            assert result1 == 3
            assert result2 == 7
            assert call_count == 2
            # set 应被调用两次（两个不同的缓存键）
            assert mock_client.set.call_count == 2

    @pytest.mark.asyncio
    async def test_cached_decorator_cache_hit(self):
        """缓存装饰器命中 - 不应执行原函数。"""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value="cached_value")
        mock_client.set = AsyncMock()

        call_count = 0

        async def expensive_compute() -> str:
            nonlocal call_count
            call_count += 1
            return "fresh_value"

        with patch.object(RedisClient, 'get_instance', new=AsyncMock(return_value=mock_client)):
            decorated = cached(ttl=300)(expensive_compute)

            result = await decorated()
            assert result == "cached_value"
            assert call_count == 0  # 未执行原函数
            mock_client.set.assert_not_called()


class TestCacheUtility:
    """缓存工具函数测试。"""

    @pytest.mark.asyncio
    async def test_get_cached_or_compute(self):
        """get_cached_or_compute - 缓存未命中时执行计算函数。"""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=None)
        mock_client.set = AsyncMock(return_value=True)

        computed = False

        async def compute():
            nonlocal computed
            computed = True
            return "computed_value"

        with patch.object(RedisClient, 'get_instance', new=AsyncMock(return_value=mock_client)):
            result = await get_cached_or_compute("test_key", compute, ttl=60)
            assert result == "computed_value"
            assert computed is True
            mock_client.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cached_or_compute_hit(self):
        """get_cached_or_compute - 缓存命中时直接返回缓存值。"""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value="cached_value")
        mock_client.set = AsyncMock()

        computed = False

        async def compute():
            nonlocal computed
            computed = True
            return "fresh_value"

        with patch.object(RedisClient, 'get_instance', new=AsyncMock(return_value=mock_client)):
            result = await get_cached_or_compute("test_key", compute, ttl=60)
            assert result == "cached_value"
            assert computed is False  # 未执行计算函数
            mock_client.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_key_prefix(self):
        """缓存键前缀 - 应包含正确的命名空间。"""
        assert CacheKeyPrefix.DEFAULT == "manga:"
        assert CacheKeyPrefix.USER == "manga:user:"
        assert CacheKeyPrefix.PROJECT == "manga:project:"
        assert CacheKeyPrefix.SESSION == "manga:session:"

        all_prefixes = CacheKeyPrefix.all_prefixes()
        assert len(all_prefixes) >= 6
        assert "manga:" in all_prefixes
        assert "manga:user:" in all_prefixes

    @pytest.mark.asyncio
    async def test_invalidate_cache(self):
        """invalidate_cache - 应调用 clear_pattern。"""
        mock_client = AsyncMock()
        mock_client.clear_pattern = AsyncMock(return_value=5)

        with patch.object(RedisClient, 'get_instance', new=AsyncMock(return_value=mock_client)):
            result = await invalidate_cache("manga:user:*")
            assert result == 5
            mock_client.clear_pattern.assert_called_once_with("manga:user:*")