"""
Agent 后台任务
=============
异步执行 LangGraph Agent 工作流、分镜生成、提示词批量生成等耗时操作。

所有任务由 Celery Worker 异步执行，通过 asyncio.run() 驱动底层 async 代码。
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from celery import Task
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.tasks.celery_app import celery_app
from app.core.constants import ProjectStatus
from app.core.config import settings
from app.database import engine
from app.models.project import Project, Script, Storyboard

logger = logging.getLogger(__name__)

# 为 Celery 任务创建独立的异步会话工厂
async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


# ============ 工具函数 ============

async def _get_project(session: AsyncSession, project_id: str) -> Optional[Project]:
    """按 ID 获取项目"""
    result = await session.execute(
        select(Project).where(Project.id == UUID(project_id))
    )
    return result.scalar_one_or_none()


async def _update_project_status(
    session: AsyncSession,
    project_id: str,
    status: ProjectStatus,
    error_msg: Optional[str] = None,
) -> None:
    """更新项目状态"""
    values: Dict[str, Any] = {
        "status": status.value,
        "updated_at": datetime.now(timezone.utc),
    }
    if error_msg:
        values["description"] = error_msg  # 将错误信息暂存到 description 字段
    await session.execute(
        update(Project).where(Project.id == UUID(project_id)).values(**values)
    )
    await session.commit()


async def _push_progress(
    project_id: str,
    event: str,
    data: Dict[str, Any],
) -> None:
    """
    通过 Redis Pub/Sub 推送进度事件。
    WebSocket / SSE 服务端订阅对应 channel 后转发给前端。

    订阅 channel: project:{project_id}:progress
    """
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.REDIS_URL)
        message = json.dumps({"event": event, "data": data, "timestamp": datetime.now(timezone.utc).isoformat()})
        await r.publish(f"project:{project_id}:progress", message)
        await r.aclose()  # type: ignore[attr-defined]
    except Exception:
        logger.warning("推送进度事件失败 (project=%s, event=%s)", project_id, event, exc_info=True)


# ============ 异步任务核心逻辑 ============

async def _run_workflow_async(project_id: str) -> None:
    """异步执行 Agent 工作流"""
    session = async_session_factory()
    try:
        # 1. 获取项目信息
        project = await _get_project(session, project_id)
        if not project:
            logger.error("项目不存在: %s", project_id)
            return

        logger.info("开始执行 Agent 工作流: project=%s name=%s", project_id, project.name)

        # 2. 更新状态为 generating
        await _update_project_status(session, project_id, ProjectStatus.GENERATING)
        await _push_progress(project_id, "status", {"status": "generating", "message": "开始生成..."})

        # 3. 导入工作流（延迟导入，避免循环依赖）
        from app.agents.workflow import manga_workflow

        # 构造初始状态
        initial_state: Dict[str, Any] = {
            "project_id": project_id,
            "project_name": project.name,
            "genre": project.genre,
            "story_input": project.story_input,
            # 策划阶段
            "world_setting": None,
            "central_conflict": None,
            "theme": None,
            "target_audience": None,
            "style_reference": None,
            # 角色
            "characters": [],
            # 剧本
            "script": None,
            "script_outline": None,
            "chapters": None,
            # 分镜
            "storyboards": [],
            "current_scene": None,
            "current_panel": None,
            # 提示词
            "prompts": [],
            # 质量检查
            "quality_report": None,
            "revision_notes": None,
            "passed_quality": False,
            # 流程控制
            "error": None,
            "error_count": 0,
            "needs_human_approval": False,
            "status": "planning",
        }

        # 4. 执行工作流（同步执行，但内部图遍历是同步的）
        #    LangGraph 的 StateGraph.run() 是同步的，因此直接调用即可
        thread_id = f"project_{project_id}"
        config = {"configurable": {"thread_id": thread_id}}

        # 推送进度
        await _push_progress(project_id, "workflow_start", {
            "message": "工作流已启动",
            "thread_id": thread_id,
        })

        # 执行工作流（同步调用，但在异步上下文中通过 run_in_executor 避免阻塞事件循环）
        loop = asyncio.get_running_loop()
        final_state = await loop.run_in_executor(
            None,
            lambda: manga_workflow.invoke(initial_state, config=config),
        )

        # 5. 检查结果
        if final_state.get("error"):
            error_msg = final_state["error"]
            logger.error("工作流执行失败: %s", error_msg)
            await _update_project_status(session, project_id, ProjectStatus.FAILED, error_msg)
            await _push_progress(project_id, "status", {
                "status": "failed",
                "message": error_msg,
            })
            return

        # 6. 更新为完成状态
        await _update_project_status(session, project_id, ProjectStatus.COMPLETED)
        await _push_progress(project_id, "status", {
            "status": "completed",
            "message": "生成完成",
            "summary": {
                "characters_count": len(final_state.get("characters", [])),
                "storyboards_count": len(final_state.get("storyboards", [])),
                "prompts_count": len(final_state.get("prompts", [])),
                "passed_quality": final_state.get("passed_quality", False),
            },
        })

        logger.info("Agent 工作流执行完成: project=%s", project_id)

    except Exception as exc:
        logger.exception("Agent 工作流异常: project=%s", project_id)
        try:
            await _update_project_status(session, project_id, ProjectStatus.FAILED, str(exc))
            await _push_progress(project_id, "status", {
                "status": "failed",
                "message": f"系统异常: {exc}",
            })
        except Exception:
            logger.exception("更新项目失败状态时出错: project=%s", project_id)
    finally:
        await session.close()


async def _generate_storyboard_async(project_id: str, script_id: str) -> None:
    """异步生成分镜"""
    session = async_session_factory()
    try:
        project = await _get_project(session, project_id)
        if not project:
            logger.error("项目不存在: %s", project_id)
            return

        # 获取剧本
        result = await session.execute(
            select(Script).where(Script.id == UUID(script_id))
        )
        script = result.scalar_one_or_none()
        if not script:
            logger.error("剧本不存在: %s", script_id)
            return

        await _push_progress(project_id, "storyboard_start", {
            "script_id": script_id,
            "message": "开始生成分镜...",
        })

        # 调用 StoryboardAgent 生成分镜
        from app.agents.storyboarder import StoryboardAgent

        storyboarder = StoryboardAgent()
        scenes = script.scenes if isinstance(script.scenes, list) else []

        for scene_idx, scene in enumerate(scenes):
            scene_data = {
                "script_id": script_id,
                "scene_number": scene_idx + 1,
                "scene_description": scene.get("description", ""),
                "characters": scene.get("characters", []),
                "dialogue": scene.get("dialogue", ""),
            }

            # 生成该场景的分镜
            result = storyboarder.generate_scene_storyboard(scene_data)  # type: ignore[attr-defined]

            # 保存到数据库
            for panel in result.get("panels", []):
                storyboard = Storyboard(
                    project_id=UUID(project_id),
                    script_id=UUID(script_id),
                    scene_number=scene_idx + 1,
                    panel_number=panel.get("panel_number", 1),
                    description=panel.get("description", ""),
                    composition=panel.get("composition", ""),
                    dialogue=panel.get("dialogue", ""),
                    camera_angle=panel.get("camera_angle", ""),
                    prompt=panel.get("prompt", ""),
                    status="completed",
                )
                session.add(storyboard)

            await session.commit()
            await _push_progress(project_id, "storyboard_progress", {
                "scene": scene_idx + 1,
                "total_scenes": len(scenes),
                "message": f"场景 {scene_idx + 1}/{len(scenes)} 分镜已生成",
            })

        await _push_progress(project_id, "storyboard_complete", {
            "message": "分镜生成完成",
        })
        logger.info("分镜生成完成: project=%s script=%s", project_id, script_id)

    except Exception as exc:
        logger.exception("生成分镜异常: project=%s script=%s", project_id, script_id)
        await _push_progress(project_id, "storyboard_error", {
            "message": f"分镜生成失败: {exc}",
        })
    finally:
        await session.close()


async def _batch_generate_prompts_async(project_id: str) -> None:
    """异步批量生成提示词"""
    session = async_session_factory()
    try:
        project = await _get_project(session, project_id)
        if not project:
            logger.error("项目不存在: %s", project_id)
            return

        # 获取所有待生成提示词的分镜
        result = await session.execute(
            select(Storyboard)
            .where(Storyboard.project_id == UUID(project_id))
            .where(Storyboard.status == "pending")
            .order_by(Storyboard.scene_number, Storyboard.panel_number)
        )
        pending_storyboards = result.scalars().all()

        if not pending_storyboards:
            logger.info("没有待生成提示词的分镜: project=%s", project_id)
            await _push_progress(project_id, "prompt_batch_complete", {
                "message": "没有待处理的分镜",
                "total": 0,
            })
            return

        await _push_progress(project_id, "prompt_batch_start", {
            "total": len(pending_storyboards),
            "message": f"开始批量生成 {len(pending_storyboards)} 个提示词...",
        })

        # 调用 PromptAgent 生成提示词
        from app.agents.prompter import PromptAgent

        prompter = PromptAgent()

        for idx, sb in enumerate(pending_storyboards):
            panel_data = {
                "project_name": project.name,
                "genre": project.genre,
                "scene_number": sb.scene_number,
                "panel_number": sb.panel_number,
                "description": sb.description,
                "composition": sb.composition,
                "dialogue": sb.dialogue,
                "camera_angle": sb.camera_angle,
            }

            # 生成提示词（假设 PromptAgent 有 generate_prompt 方法）
            prompt_result = prompter.generate_prompt(panel_data)  # type: ignore[attr-defined]
            generated_prompt = prompt_result.get("prompt", "")

            # 更新分镜记录
            await session.execute(
                update(Storyboard)
                .where(Storyboard.id == sb.id)
                .values(prompt=generated_prompt, status="completed")
            )
            await session.commit()

            await _push_progress(project_id, "prompt_batch_progress", {
                "current": idx + 1,
                "total": len(pending_storyboards),
                "storyboard_id": str(sb.id),
                "message": f"提示词 {idx + 1}/{len(pending_storyboards)} 已生成",
            })

        await _push_progress(project_id, "prompt_batch_complete", {
            "total": len(pending_storyboards),
            "message": f"批量生成完成，共 {len(pending_storyboards)} 个提示词",
        })
        logger.info("批量提示词生成完成: project=%s count=%s", project_id, len(pending_storyboards))

    except Exception as exc:
        logger.exception("批量生成提示词异常: project=%s", project_id)
        await _push_progress(project_id, "prompt_batch_error", {
            "message": f"批量生成提示词失败: {exc}",
        })
    finally:
        await session.close()


# ============ Celery 任务 ============


@celery_app.task(
    bind=True,
    name="app.tasks.agent_tasks.run_agent_workflow",
    autoretry_for=(Exception,),
    max_retries=2,
    default_retry_delay=120,
    acks_late=True,
)
def run_agent_workflow(
    self: Task,
    project_id: str,
) -> Dict[str, Any]:
    """
    异步执行 LangGraph Agent 工作流。

    这是一个 Celery 任务，内部通过 asyncio.run() 驱动异步代码。
    支持自动重试（最多 2 次，间隔 120 秒）。

    Args:
        project_id: 项目 UUID 字符串

    Returns:
        Dict[str, Any]: 任务结果摘要
    """
    logger.info("收到 Agent 工作流任务: project=%s task_id=%s", project_id, self.request.id)

    try:
        asyncio.run(_run_workflow_async(project_id))
        return {"project_id": project_id, "status": "completed", "task_id": self.request.id}
    except Exception as exc:
        logger.exception("run_agent_workflow 任务失败: project=%s", project_id)
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    name="app.tasks.agent_tasks.generate_storyboard",
    autoretry_for=(Exception,),
    max_retries=2,
    default_retry_delay=60,
)
def generate_storyboard(
    self: Task,
    project_id: str,
    script_id: str,
) -> Dict[str, Any]:
    """
    异步生成分镜。

    根据剧本内容，调用 StoryboardAgent 逐场景生成分镜面板，
    并将结果持久化到数据库。

    Args:
        project_id: 项目 UUID 字符串
        script_id: 剧本 UUID 字符串

    Returns:
        Dict[str, Any]: 任务结果摘要
    """
    logger.info("收到分镜生成任务: project=%s script=%s", project_id, script_id)

    try:
        asyncio.run(_generate_storyboard_async(project_id, script_id))
        return {
            "project_id": project_id,
            "script_id": script_id,
            "status": "completed",
            "task_id": self.request.id,
        }
    except Exception as exc:
        logger.exception("generate_storyboard 任务失败: project=%s", project_id)
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    name="app.tasks.agent_tasks.batch_generate_prompts",
    autoretry_for=(Exception,),
    max_retries=2,
    default_retry_delay=60,
)
def batch_generate_prompts(
    self: Task,
    project_id: str,
) -> Dict[str, Any]:
    """
    批量生成提示词。

    遍历项目中所有状态为 'pending' 的分镜记录，
    调用 PromptAgent 为每个分镜生成 AI 绘图提示词。

    Args:
        project_id: 项目 UUID 字符串

    Returns:
        Dict[str, Any]: 任务结果摘要
    """
    logger.info("收到批量提示词生成任务: project=%s", project_id)

    try:
        asyncio.run(_batch_generate_prompts_async(project_id))
        return {"project_id": project_id, "status": "completed", "task_id": self.request.id}
    except Exception as exc:
        logger.exception("batch_generate_prompts 任务失败: project=%s", project_id)
        raise self.retry(exc=exc)