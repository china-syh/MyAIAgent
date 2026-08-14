"""
LangGraph 工作流编排 —— 课件模式重写
create_agent(07) + HumanInTheLoop(08) + 上下文记忆(09) + LangSmith(03) + Tools(05)
"""
import logging
import os
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from typing_extensions import TypedDict
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.tracers import LangChainTracer
from langchain_core.runnables import RunnableConfig

from app.agents.planner import PlanningAgent
from app.agents.writer import WritingAgent
from app.agents.storyboarder import StoryboardAgent
from app.agents.prompter import PromptAgent
from app.agents.quality_checker import QualityCheckerAgent
from app.core.config import settings

logger = logging.getLogger(__name__)


# ===== 课件03: LangSmith 回调处理 =====
def setup_langsmith_tracing() -> list:
    """配置 LangSmith 追踪 —— 课件03: LangSmith 的使用"""
    callbacks = []
    if settings.LANGSMITH_TRACING and settings.LANGSMITH_API_KEY:
        try:
            os.environ["LANGSMITH_TRACING"] = "true"
            os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
            os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT
            os.environ["LANGSMITH_ENDPOINT"] = settings.LANGSMITH_ENDPOINT

            tracer = LangChainTracer(
                project_name=settings.LANGSMITH_PROJECT,
            )
            callbacks.append(tracer)
            logger.info(f"✅ [课件03] LangSmith 追踪已启用: {settings.LANGSMITH_PROJECT}")
        except Exception as e:
            logger.warning(f"LangSmith 追踪启用失败: {e}")
    else:
        logger.info("📝 [课件03] LangSmith 未配置，跳过追踪")
    return callbacks


# ===== 课件09: 共享状态 =====
class MangaState(TypedDict):
    """漫画制作工作流共享状态"""
    # 输入
    story_input: str
    genre: str
    project_id: str

    # 策划输出
    chapter_title: str
    world_setting: str
    central_conflict: str
    theme: str
    target_audience: str
    style_reference: str
    characters: list
    scenes: list

    # 剧本输出
    script: dict

    # 分镜输出
    storyboards: list

    # 提示词输出
    prompts: list

    # 质量检查输出
    passed_quality: bool
    quality_report: dict
    revision_notes: list

    # 状态跟踪
    status: str
    error: str
    error_count: int
    quality_retry_count: int


def create_initial_state(story_input: str = "", genre: str = "fantasy", project_id: str = "") -> MangaState:
    """创建初始状态 — 课件09: 上下文初始化管理"""
    return {
        "story_input": story_input,
        "genre": genre,
        "project_id": project_id,
        "chapter_title": "",
        "world_setting": "",
        "central_conflict": "",
        "theme": "",
        "target_audience": "",
        "style_reference": "",
        "characters": [],
        "scenes": [],
        "script": {},
        "storyboards": [],
        "prompts": [],
        "passed_quality": False,
        "quality_report": {},
        "revision_notes": [],
        "status": "pending",
        "error": "",
        "error_count": 0,
        "quality_retry_count": 0,
    }


# ===== 各 Agent 节点（课件03: 传入 LangSmith callbacks） =====
_global_callbacks = setup_langsmith_tracing()


def planner_node(state: MangaState) -> MangaState:
    """策划节点"""
    logger.info("📋 [工作流] 执行策划节点...")
    agent = PlanningAgent()
    # 课件03: 传入 LangSmith 回调
    if _global_callbacks:
        agent.chain.callbacks = _global_callbacks
    result = agent.run(state)
    if result.get("error"):
        return {**state, "status": "failed", "error": result["error"], "error_count": state.get("error_count", 0) + 1}
    return {
        **state,
        **result,
        "status": "planning_completed",
    }


def writer_node(state: MangaState) -> MangaState:
    """编剧节点"""
    logger.info("📋 [工作流] 执行编剧节点...")
    agent = WritingAgent()
    if _global_callbacks:
        agent.chain.callbacks = _global_callbacks
    result = agent.run(state)
    if result.get("error"):
        return {**state, "status": "failed", "error": result["error"], "error_count": state.get("error_count", 0) + 1}
    return {
        **state,
        **result,
        "status": "writing_completed",
    }


def storyboarder_node(state: MangaState) -> MangaState:
    """分镜节点"""
    logger.info("📋 [工作流] 执行分镜节点...")
    agent = StoryboardAgent()
    if _global_callbacks:
        # 设置所有 chain 的回调
        pass
    result = agent.run(state)
    if result.get("error"):
        return {**state, "status": "failed", "error": result["error"], "error_count": state.get("error_count", 0) + 1}
    return {
        **state,
        **result,
        "status": "storyboarding_completed",
    }


def prompter_node(state: MangaState) -> MangaState:
    """提示词节点"""
    logger.info("📋 [工作流] 执行提示词节点...")
    agent = PromptAgent()
    if _global_callbacks:
        agent.chain.callbacks = _global_callbacks
    result = agent.run(state)
    if result.get("error"):
        return {**state, "status": "failed", "error": result["error"], "error_count": state.get("error_count", 0) + 1}
    return {
        **state,
        **result,
        "status": "prompting_completed",
    }


def quality_checker_node(state: MangaState) -> MangaState:
    """质量检查节点"""
    logger.info("📋 [工作流] 执行质量检查节点...")
    agent = QualityCheckerAgent()
    if _global_callbacks:
        agent.chain.callbacks = _global_callbacks
    result = agent.run(state)
    if result.get("error"):
        return {**state, "status": "failed", "error": result["error"], "error_count": state.get("error_count", 0) + 1}
    return {
        **state,
        **result,
        "status": "quality_completed",
    }


# ===== 路由函数 =====
def route_after_quality(state: MangaState) -> Literal["prompter", END]:
    """课件08: 质量检查路由 — 不通过则重试（最多3次），通过则结束"""
    if not state.get("passed_quality", False):
        retry_count = state.get("quality_retry_count", 0) + 1
        if retry_count >= 3:
            logger.warning("质量检查已重试 3 次，结束流程")
            return END
        logger.info(f"质量检查未通过，重试第 {retry_count} 次")
        return "prompter"
    return END


# ===== 构建工作流图 =====
def build_manga_workflow():
    """构建漫画制作工作流图 — 课件07: 智能体编排"""
    workflow = StateGraph(MangaState)

    # 添加节点
    workflow.add_node("planner", planner_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("storyboarder", storyboarder_node)
    workflow.add_node("prompter", prompter_node)
    workflow.add_node("quality_checker", quality_checker_node)

    # 添加边
    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "writer")
    workflow.add_edge("writer", "storyboarder")
    workflow.add_edge("storyboarder", "prompter")
    workflow.add_edge("prompter", "quality_checker")
    workflow.add_conditional_edges(
        "quality_checker",
        route_after_quality,
        {"prompter": "prompter", END: END},
    )

    # 课件08: HumanInTheLoop — 在质量检查前插入人工审批
    # 课件09: MemorySaver 作为检查点
    checkpointer = MemorySaver()
    app = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["quality_checker"],  # 课件08: 质量检查前暂停，等待人工确认
    )

    return app


# 创建全局工作流实例
manga_workflow = build_manga_workflow()

# 兼容旧接口名
create_manga_workflow = build_manga_workflow
