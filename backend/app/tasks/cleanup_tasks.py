"""
清理与维护任务
=============
由 Celery Beat 定时触发的系统维护任务，包括：
- 临时文件清理（超过 24 小时）
- 过期刷新令牌清理
- 旧项目归档（超过 90 天）
"""

import asyncio
import logging
import os
import shutil
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from uuid import UUID

from celery import Task
from sqlalchemy import select, update

from app.tasks.celery_app import celery_app
from app.core.config import settings
from app.database import engine
from app.models.project import Project
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)

# 为 Celery 任务创建独立的异步会话工厂
async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


# ============ 异步核心逻辑 ============


async def _cleanup_temp_files_async() -> Dict[str, Any]:
    """
    清理超过 24 小时的临时文件。

    扫描以下目录中超过 24 小时未修改的文件并删除：
    - UPLOAD_DIR / temp
    - 系统临时目录中的应用相关文件

    Returns:
        Dict[str, Any]: 清理结果统计
    """
    result: Dict[str, Any] = {
        "deleted_files": 0,
        "deleted_dirs": 0,
        "freed_bytes": 0,
        "errors": [],
    }

    # 需要扫描的临时目录列表
    temp_dirs: List[str] = []

    # 1. 配置的上传目录下的 temp 子目录
    upload_temp = os.path.join(settings.UPLOAD_DIR, "temp")
    if os.path.isdir(upload_temp):
        temp_dirs.append(upload_temp)

    # 2. 系统临时目录
    system_temp = os.environ.get("TEMP") or os.environ.get("TMP") or "/tmp"
    app_temp = os.path.join(system_temp, "ai_manga_agent")
    if os.path.isdir(app_temp):
        temp_dirs.append(app_temp)

    # 3. 项目 uploads 目录下的 temp（相对于项目根目录）
    project_upload_temp = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "uploads",
        "temp",
    )
    if os.path.isdir(project_upload_temp) and project_upload_temp not in temp_dirs:
        temp_dirs.append(project_upload_temp)

    cutoff_time = time.time() - 24 * 3600  # 24 小时前的时间戳

    for temp_dir in temp_dirs:
        logger.info("开始清理临时目录: %s", temp_dir)
        try:
            for root, dirs, files in os.walk(temp_dir, topdown=False):
                # 清理文件
                for name in files:
                    filepath = os.path.join(root, name)
                    try:
                        stat_info = os.stat(filepath)
                        if stat_info.st_mtime < cutoff_time:
                            file_size = stat_info.st_size
                            os.remove(filepath)
                            result["deleted_files"] += 1
                            result["freed_bytes"] += file_size
                            logger.debug("已删除临时文件: %s (%d bytes)", filepath, file_size)
                    except OSError as e:
                        result["errors"].append(f"删除文件失败 {filepath}: {e}")
                        logger.warning("删除文件失败: %s - %s", filepath, e)

                # 清理空目录
                for name in dirs:
                    dirpath = os.path.join(root, name)
                    try:
                        if not os.listdir(dirpath):  # 空目录
                            os.rmdir(dirpath)
                            result["deleted_dirs"] += 1
                            logger.debug("已删除空目录: %s", dirpath)
                    except OSError as e:
                        result["errors"].append(f"删除目录失败 {dirpath}: {e}")
                        logger.warning("删除目录失败: %s - %s", dirpath, e)
        except Exception as exc:
            error_msg = f"扫描临时目录失败 {temp_dir}: {exc}"
            result["errors"].append(error_msg)
            logger.exception(error_msg)

    result["freed_mb"] = round(result["freed_bytes"] / (1024 * 1024), 2)
    logger.info(
        "临时文件清理完成: 删除 %d 个文件, %d 个目录, 释放 %.2f MB",
        result["deleted_files"],
        result["deleted_dirs"],
        result["freed_mb"],
    )
    return result


async def _cleanup_expired_tokens_async() -> Dict[str, Any]:
    """
    清理过期的刷新令牌。

    当前项目使用 JWT 无状态令牌，不存储 refresh_token 到数据库。
    此函数为预留扩展点，当将来引入 RefreshToken 模型时启用。

    如需启用，请创建 RefreshToken 模型并取消下方注释:
        class RefreshToken(Base):
            __tablename__ = "refresh_tokens"
            id = Column(UUID, primary_key=True)
            user_id = Column(UUID, ForeignKey("users.id"))
            token = Column(String(500), unique=True)
            expires_at = Column(DateTime)
            is_revoked = Column(Boolean, default=False)

    然后在此函数中执行:
        stmt = delete(RefreshToken).where(
            or_(
                RefreshToken.expires_at < datetime.now(timezone.utc),
                RefreshToken.is_revoked == True,
            )
        )
        await session.execute(stmt)
        await session.commit()

    Returns:
        Dict[str, Any]: 清理结果统计
    """
    # 当前为占位实现：仅记录日志
    logger.info(
        "过期令牌清理任务执行 (跳过): 当前使用 JWT 无状态令牌，无需持久化清理。"
        "如需启用，请创建 RefreshToken 模型并更新 _cleanup_expired_tokens_async。"
    )
    return {
        "status": "skipped",
        "message": "当前使用 JWT 无状态令牌，无需持久化清理",
        "deleted_tokens": 0,
    }


async def _archive_old_projects_async(days: int = 90) -> Dict[str, Any]:
    """
    归档超过指定天数的旧项目。

    将超过 `days` 天未更新的项目标记为 is_active=False，
    逻辑删除而非物理删除，保留数据可追溯。

    Args:
        days: 天数阈值，默认 90 天

    Returns:
        Dict[str, Any]: 归档结果统计
    """
    session = async_session_factory()
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        # 查询需要归档的项目
        result = await session.execute(
            select(Project)
            .where(Project.updated_at < cutoff_date)
            .where(Project.is_active == True)  # noqa: E712
        )
        projects_to_archive = result.scalars().all()
        project_ids = [str(p.id) for p in projects_to_archive]

        if not project_ids:
            logger.info("没有需要归档的旧项目 (阈值: %d 天)", days)
            return {
                "status": "completed",
                "archived_count": 0,
                "days_threshold": days,
                "archived_project_ids": [],
            }

        # 批量更新为 inactive
        await session.execute(
            update(Project)
            .where(Project.updated_at < cutoff_date)
            .where(Project.is_active == True)  # noqa: E712
            .values(
                is_active=False,
                updated_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()

        logger.info(
            "旧项目归档完成: 归档 %d 个项目 (阈值: %d 天)",
            len(project_ids),
            days,
        )
        return {
            "status": "completed",
            "archived_count": len(project_ids),
            "days_threshold": days,
            "archived_project_ids": project_ids,
        }
    except Exception as exc:
        logger.exception("归档旧项目失败")
        return {
            "status": "failed",
            "error": str(exc),
            "archived_count": 0,
            "days_threshold": days,
        }
    finally:
        await session.close()


# ============ Celery 任务 ============


@celery_app.task(
    bind=True,
    name="app.tasks.cleanup_tasks.cleanup_temp_files",
    acks_late=True,
)
def cleanup_temp_files(self: Task) -> Dict[str, Any]:
    """
    清理超过 24 小时的临时文件。

    由 Celery Beat 定时触发（默认每天凌晨 3:00）。

    Returns:
        Dict[str, Any]: 清理结果统计
    """
    logger.info("开始执行临时文件清理任务: task_id=%s", self.request.id)

    try:
        result = asyncio.run(_cleanup_temp_files_async())
        logger.info("临时文件清理任务完成: %s", result)
        return result
    except Exception as exc:
        logger.exception("临时文件清理任务失败")
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    name="app.tasks.cleanup_tasks.cleanup_expired_tokens",
    acks_late=True,
)
def cleanup_expired_tokens(self: Task) -> Dict[str, Any]:
    """
    清理过期的刷新令牌。

    由 Celery Beat 定时触发（默认每天凌晨 3:30）。
    当前为预留占位实现；项目使用 JWT 无状态令牌无需持久化清理。

    Returns:
        Dict[str, Any]: 清理结果统计
    """
    logger.info("开始执行过期令牌清理任务: task_id=%s", self.request.id)

    try:
        result = asyncio.run(_cleanup_expired_tokens_async())
        logger.info("过期令牌清理任务完成: %s", result)
        return result
    except Exception as exc:
        logger.exception("过期令牌清理任务失败")
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    name="app.tasks.cleanup_tasks.archive_old_projects",
    acks_late=True,
)
def archive_old_projects(
    self: Task,
    days: int = 90,
) -> Dict[str, Any]:
    """
    归档超过指定天数的旧项目（逻辑删除，标记 is_active=False）。

    由 Celery Beat 定时触发（默认每月 1 日凌晨 4:00）。
    也可手动调用执行:
        archive_old_projects.delay(days=90)

    Args:
        days: 天数阈值，默认 90 天

    Returns:
        Dict[str, Any]: 归档结果统计
    """
    logger.info("开始执行旧项目归档任务: task_id=%s days=%d", self.request.id, days)

    try:
        result = asyncio.run(_archive_old_projects_async(days=days))
        logger.info("旧项目归档任务完成: %s", result)
        return result
    except Exception as exc:
        logger.exception("旧项目归档任务失败")
        raise self.retry(exc=exc)