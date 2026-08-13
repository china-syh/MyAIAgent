import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.metrics import setup_metrics
from app.core.logger import configure_logging, get_logger, set_correlation_id, LoggerContext
from app.core.cache import init_cache, close_cache
from app.middleware import RequestLogMiddleware
from app.database import init_db, engine
from app.api.v1 import api_v1_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动阶段
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动中...")

    # 1. 初始化日志系统
    configure_logging()
    logger.info("✅ 日志系统初始化完成")

    # 2. 创建 generated 目录
    os.makedirs("generated/images", exist_ok=True)
    os.makedirs("generated/videos", exist_ok=True)
    logger.info("✅ 生成文件目录初始化完成")

    # 3. 初始化数据库
    try:
        await init_db()
        logger.info("✅ 数据库表初始化完成")
    except Exception as e:
        logger.warning(f"⚠️ 数据库初始化跳过: {e}")

    # 4. 初始化缓存
    try:
        await init_cache()
        logger.info("✅ Redis 缓存初始化完成")
    except Exception as e:
        logger.warning(f"⚠️ Redis 缓存初始化跳过: {e}")

    yield

    # 关闭阶段
    logger.info("👋 服务关闭中...")
    try:
        await close_cache()
        logger.info("✅ Redis 连接已关闭")
    except Exception as e:
        logger.warning(f"⚠️ Redis 关闭异常: {e}")
    logger.info("✅ 服务已关闭")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI 漫剧 Agent - 智能漫画创作平台 - 企业版",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "AI 漫剧 Agent 团队",
        "url": "https://github.com/ai-manga-agent",
    },
    license_info={
        "name": "MIT",
    },
)

# 中间件（按顺序：外到内）
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)
app.add_middleware(CORSMiddleware, **settings.cors_args)
app.add_middleware(RequestLogMiddleware)

# 请求追踪 ID 中间件
@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID") or ""
    set_correlation_id(correlation_id)
    with LoggerContext(correlation_id=correlation_id, path=request.url.path):
        response = await call_next(request)
    if correlation_id:
        response.headers["X-Correlation-ID"] = correlation_id
    return response

# 全局异常处理
register_exception_handlers(app)

# 路由
app.include_router(api_v1_router, prefix="/api/v1")

# 静态文件服务（用于提供生成的图片和视频）
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp

class CORSStaticMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response

static_app = StaticFiles(directory="generated")
static_app = CORSStaticMiddleware(static_app)
app.mount("/generated", static_app, name="generated")

# Prometheus 监控（中间件 + /metrics 端点）
setup_metrics(app)


# 健康检查
@app.get("/api/health")
async def health_check():
    import time
    from app.core.cache import RedisClient
    from app.core.metrics import update_db_pool_metrics

    # 数据库连接池指标
    if engine.pool and hasattr(engine.pool, "size"):
        update_db_pool_metrics(
            pool_name="default",
            pool_size=engine.pool.size(),
            active=len(engine.pool._checkedout) if hasattr(engine.pool, "_checkedout") else 0,
        )

    # 缓存健康检查
    cache_ok = False
    cache_latency = 0
    try:
        start = time.time()
        cache = await RedisClient.get_instance()
        await cache.set("health_check", "ok", ttl=5)
        cache_ok = True
        cache_latency = round((time.time() - start) * 1000, 2)
    except Exception:
        pass

    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENV,
        "checks": {
            "database": "connected" if engine.pool else "disconnected",
            "cache": "connected" if cache_ok else "disconnected",
            "cache_latency_ms": cache_latency,
        },
        "timestamp": int(time.time()),
    }
