"""
企业级后台任务系统
================
基于 Celery 的异步任务队列，支持：
- LangGraph Agent 工作流异步执行
- 分镜与提示词生成
- 定时清理与维护任务

启动 Worker:
    celery -A app.tasks.celery_app worker -l info -Q agent,cleanup

启动 Beat (定时任务):
    celery -A app.tasks.celery_app beat -l info

同时启动 Worker + Beat:
    celery -A app.tasks.celery_app worker -B -l info -Q agent,cleanup
"""

from app.tasks.celery_app import celery_app
from app.tasks.agent_tasks import (
    run_agent_workflow,
    generate_storyboard,
    batch_generate_prompts,
)
from app.tasks.cleanup_tasks import (
    cleanup_temp_files,
    cleanup_expired_tokens,
    archive_old_projects,
)

__all__ = [
    # Celery 应用实例
    "celery_app",
    # Agent 任务
    "run_agent_workflow",
    "generate_storyboard",
    "batch_generate_prompts",
    # 清理任务
    "cleanup_temp_files",
    "cleanup_expired_tokens",
    "archive_old_projects",
]