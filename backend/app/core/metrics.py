"""
Prometheus 监控指标模块

提供应用级监控指标，包括：
- HTTP 请求计数器（按路径、方法、状态码）
- HTTP 请求延迟直方图
- 活跃请求数（Gauge）
- 数据库连接池大小
- 缓存命中率
- Prometheus 中间件（自动采集）
- /metrics 端点注册函数
"""

import time
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, Response
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
    REGISTRY,
    CollectorRegistry,
)
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("manga.metrics")

# ---------------------------------------------------------------------------
# 自定义 Registry（避免与全局默认 registry 冲突）
# ---------------------------------------------------------------------------
metrics_registry: CollectorRegistry = CollectorRegistry()
_dummy_registry = REGISTRY  # 确保 prometheus_client 模块已加载

# ---------------------------------------------------------------------------
# HTTP 请求指标
# ---------------------------------------------------------------------------

http_request_total = Counter(
    name="manga_http_request_total",
    documentation="HTTP 请求总数，按路径、方法、状态码划分",
    labelnames=["path", "method", "status_code"],
    registry=metrics_registry,
)

http_request_duration_seconds = Histogram(
    name="manga_http_request_duration_seconds",
    documentation="HTTP 请求延迟分布（秒）",
    labelnames=["path", "method"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
    registry=metrics_registry,
)

http_active_requests = Gauge(
    name="manga_http_active_requests",
    documentation="当前正在处理的 HTTP 请求数",
    registry=metrics_registry,
)

# ---------------------------------------------------------------------------
# 业务指标
# ---------------------------------------------------------------------------

db_connection_pool_size = Gauge(
    name="manga_db_connection_pool_size",
    documentation="数据库连接池当前大小",
    labelnames=["pool_name"],
    registry=metrics_registry,
)

db_connection_active = Gauge(
    name="manga_db_connection_active",
    documentation="数据库连接池活跃连接数",
    labelnames=["pool_name"],
    registry=metrics_registry,
)

cache_hit_total = Counter(
    name="manga_cache_hit_total",
    documentation="缓存命中总数",
    labelnames=["cache_prefix"],
    registry=metrics_registry,
)

cache_miss_total = Counter(
    name="manga_cache_miss_total",
    documentation="缓存未命中总数",
    labelnames=["cache_prefix"],
    registry=metrics_registry,
)

cache_operation_duration_seconds = Histogram(
    name="manga_cache_operation_duration_seconds",
    documentation="缓存操作延迟分布（秒）",
    labelnames=["operation"],  # get / set / delete
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
    registry=metrics_registry,
)

# ---------------------------------------------------------------------------
# 应用级指标
# ---------------------------------------------------------------------------

app_info = Gauge(
    name="manga_app_info",
    documentation="应用基本信息（固定为 1，通过 label 传递版本和环境）",
    labelnames=["app_name", "version", "environment"],
    registry=metrics_registry,
)

task_queue_size = Gauge(
    name="manga_task_queue_size",
    documentation="Celery 任务队列大小",
    labelnames=["queue_name"],
    registry=metrics_registry,
)

# 设置应用信息（启动时由 setup_metrics 调用）
app_info.labels(
    app_name=settings.APP_NAME,
    version=settings.APP_VERSION,
    environment=settings.ENV,
).set(1)

# ---------------------------------------------------------------------------
# Prometheus 中间件
# ---------------------------------------------------------------------------


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    FastAPI 中间件，自动采集 HTTP 请求指标。

    用法::

        app.add_middleware(PrometheusMiddleware)
    """

    # 不需要监控的路径白名单
    EXCLUDED_PATHS: tuple = ("/metrics", "/health", "/api/health", "/docs", "/redoc", "/openapi.json")

    async def dispatch(self, request: Request, call_next) -> Response:
        # 跳过白名单路径
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        # 活跃请求数 +1
        http_active_requests.inc()

        method = request.method
        path = request.url.path

        start_time = time.monotonic()
        try:
            response: Response = await call_next(request)
            return response
        finally:
            # 请求持续时间
            duration = time.monotonic() - start_time
            status_code = str(response.status_code) if "response" in dir() and response else "500"

            # 记录指标
            http_request_total.labels(path=path, method=method, status_code=status_code).inc()
            http_request_duration_seconds.labels(path=path, method=method).observe(duration)
            http_active_requests.dec()

            logger.debug(
                "Metrics: %s %s -> %s (%.3fs)",
                method, path, status_code, duration,
            )


# ---------------------------------------------------------------------------
# 指标更新辅助函数
# ---------------------------------------------------------------------------


def update_db_pool_metrics(pool_name: str = "default", pool_size: int = 0, active: int = 0) -> None:
    """更新数据库连接池指标。"""
    db_connection_pool_size.labels(pool_name=pool_name).set(pool_size)
    db_connection_active.labels(pool_name=pool_name).set(active)


def record_cache_hit(cache_prefix: str = "manga:") -> None:
    """记录一次缓存命中。"""
    cache_hit_total.labels(cache_prefix=cache_prefix).inc()


def record_cache_miss(cache_prefix: str = "manga:") -> None:
    """记录一次缓存未命中。"""
    cache_miss_total.labels(cache_prefix=cache_prefix).inc()


def record_cache_operation(operation: str, duration: float) -> None:
    """记录缓存操作耗时。

    Args:
        operation: 操作类型，如 ``get`` / ``set`` / ``delete``
        duration: 耗时（秒）
    """
    cache_operation_duration_seconds.labels(operation=operation).observe(duration)


def get_cache_hit_rate(cache_prefix: str = "manga:") -> Optional[float]:
    """计算缓存命中率。

    Returns:
        命中率 (0.0 ~ 1.0)，若无数据则返回 None
    """
    hits = cache_hit_total.labels(cache_prefix=cache_prefix)._value.get()
    misses = cache_miss_total.labels(cache_prefix=cache_prefix)._value.get()
    total = hits + misses
    if total == 0:
        return None
    return hits / total


def update_task_queue_metrics(queue_name: str, size: int) -> None:
    """更新 Celery 任务队列大小指标。"""
    task_queue_size.labels(queue_name=queue_name).set(size)


# ---------------------------------------------------------------------------
# /metrics 端点注册
# ---------------------------------------------------------------------------


async def metrics_endpoint() -> Response:
    """返回 Prometheus 格式的指标数据。

    用法::

        app.get("/metrics")(metrics_endpoint)
    """
    data = generate_latest(metrics_registry)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


def setup_metrics(app: FastAPI) -> None:
    """初始化监控系统。

    在 FastAPI 应用启动时调用，完成以下工作：
    1. 注册 Prometheus 中间件
    2. 注册 /metrics 端点
    3. 记录应用基本信息

    Args:
        app: FastAPI 应用实例

    用法::

        from app.core.metrics import setup_metrics
        setup_metrics(app)
    """
    # 注册中间件
    app.add_middleware(PrometheusMiddleware)

    # 注册 /metrics 端点
    app.add_route("/metrics", metrics_endpoint, include_in_schema=False)

    logger.info(
        "Prometheus 监控已初始化: app=%s v=%s env=%s",
        settings.APP_NAME, settings.APP_VERSION, settings.ENV,
    )


# ---------------------------------------------------------------------------
# 装饰器：带缓存指标追踪的缓存操作
# ---------------------------------------------------------------------------


def tracked_cache_get(prefix: str = "manga:"):
    """装饰器：为缓存 get 操作添加命中率追踪。

    用法::

        @tracked_cache_get(prefix="manga:user:")
        async def get_user(user_id: int) -> dict:
            ...
    """
    from functools import wraps

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.monotonic()
            result = await func(*args, **kwargs)
            duration = time.monotonic() - start

            if result is not None:
                record_cache_hit(prefix)
            else:
                record_cache_miss(prefix)

            record_cache_operation("get", duration)
            return result
        return wrapper
    return decorator