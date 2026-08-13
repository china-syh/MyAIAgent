"""
Celery 应用配置
==============
使用 Redis 作为 broker 和 result backend 的企业级 Celery 配置。

启动 Worker:
    celery -A app.tasks.celery_app worker -l info

启动 Beat (定时任务):
    celery -A app.tasks.celery_app beat -l info

同时启动 Worker + Beat:
    celery -A app.tasks.celery_app worker -B -l info
"""

import logging
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

logger = logging.getLogger(__name__)

# ============ 创建 Celery 应用 ============

celery_app = Celery(
    "ai_manga_agent",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.agent_tasks",
        "app.tasks.cleanup_tasks",
    ],
)

# ============ 核心序列化配置 ============

celery_app.conf.update(
    # 序列化
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # 结果有效期（秒），过期自动清理
    result_expires=3600 * 24,  # 24 小时
    # 任务确认行为
    task_acks_late=True,  # 任务完成后才确认，防止丢失
    task_reject_on_worker_lost=True,  # worker 崩溃时拒绝任务，重新投递
    # Worker 配置
    worker_max_tasks_per_child=200,  # 每个 worker 最多处理 200 个任务后重启，防内存泄漏
    worker_prefetch_multiplier=1,  # 每次只预取一个任务，防止某个队列被饿死
    worker_concurrency=4,  # 并发 worker 数量，可根据服务器核数调整
    # 任务超时
    task_soft_time_limit=600,  # 软超时 10 分钟，触发 SoftTimeLimitExceeded
    task_time_limit=900,  # 硬超时 15 分钟，强制终止
    # 任务重试
    task_default_retry_delay=60,  # 默认重试间隔 60 秒
    task_max_retries=3,  # 最大重试次数
    # 可见性超时（Redis 专用）
    broker_transport_options={
        "visibility_timeout": 3600 * 2,  # 2 小时，确保长任务不被重复投递
    },
)

# ============ 定时任务 (Beat Schedule) ============

celery_app.conf.beat_schedule = {
    # 每天凌晨 3:00 清理临时文件
    "cleanup-temp-files": {
        "task": "app.tasks.cleanup_tasks.cleanup_temp_files",
        "schedule": crontab(hour=3, minute=0),
        "options": {"queue": "cleanup"},
    },
    # 每天凌晨 3:30 清理过期令牌
    "cleanup-expired-tokens": {
        "task": "app.tasks.cleanup_tasks.cleanup_expired_tokens",
        "schedule": crontab(hour=3, minute=30),
        "options": {"queue": "cleanup"},
    },
    # 每月 1 日凌晨 4:00 归档旧项目
    "archive-old-projects": {
        "task": "app.tasks.cleanup_tasks.archive_old_projects",
        "schedule": crontab(day_of_month=1, hour=4, minute=0),
        "options": {"queue": "cleanup"},
    },
}

# ============ 任务路由 ============

celery_app.conf.task_routes = {
    "app.tasks.agent_tasks.*": {"queue": "agent"},
    "app.tasks.cleanup_tasks.*": {"queue": "cleanup"},
}

# ============ 日志 ============

@celery_app.on_after_configure.connect
def setup_logging(sender, **kwargs):  # noqa: ARG001
    """配置 Celery 日志"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("Celery 应用已初始化，broker: %s", settings.REDIS_URL)