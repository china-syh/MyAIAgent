"""
AI 漫剧 Agent 工作流 - LangGraph 编排
"""
import json
import logging
from typing import TypedDict, List, Optional, Dict, Any, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.agents.planner import PlanningAgent
from app.agents.writer import WritingAgent
from app.agents.storyboarder import StoryboardAgent
from app.agents.prompter import PromptAgent
from app.agents.quality_checker import QualityCheckerAgent

logger = logging.getLogger(__name__)


# ============ 定义共享状态 ============

class MangaState(TypedDict):
    """漫剧 Agent 共享状态"""
    # 项目信息
    project_id: str
    project_name: str
    genre: str

    # 输入
    story_input: str

    # 策划阶段产出
    world_setting: Optional[Dict[str, Any]]
    central_conflict: Optional[str]
    theme: Optional[str]
    target_audience: Optional[str]
    style_reference: Optional[str]

    # 角色设定
    characters: List[Dict[str, Any]]

    # 剧本产出
    script: Optional[Dict[str, Any]]
    script_outline: Optional[List[Dict[str, Any]]]
    chapters: Optional[List[Dict[str, Any]]]

    # 分镜产出
    storyboards: List[Dict[str, Any]]
    current_scene: Optional[int]
    current_panel: Optional[int]

    # 提示词产出
    prompts: List[Dict[str, Any]]

    # 质量检查
    quality_report: Optional[Dict[str, Any]]
    revision_notes: Optional[List[str]]
    passed_quality: bool

    # 流程控制
    error: Optional[str]
    error_count: int
    needs_human_approval: bool
    status: str  # planning, writing, storyboarding, prompting, reviewing, completed, failed


# ============ 构建工作流图 ============

def create_manga_workflow():
    """创建漫剧 Agent 工作流"""

    # 实例化各个 Agent
    planner = PlanningAgent()
    writer = WritingAgent()
    storyboarder = StoryboardAgent()
    prompter = PromptAgent()
    quality_checker = QualityCheckerAgent()

    # 构建状态图
    workflow = StateGraph(MangaState)

    # 注册节点
    workflow.add_node("planner", planner.run)
    workflow.add_node("writer", writer.run)
    workflow.add_node("storyboarder", storyboarder.run)
    workflow.add_node("prompter", prompter.run)
    workflow.add_node("quality_checker", quality_checker.run)

    # 设置入口点为策划 Agent
    workflow.set_entry_point("planner")

    # 策划 -> 编剧：根据策划结果决定是否需要人工审批
    workflow.add_conditional_edges(
        "planner",
        route_after_planning,
        {
            "writer": "writer",
            "needs_approval": "writer",  # 简化处理，仍然进入编剧
            "failed": END,
        }
    )

    # 编剧 -> 分镜
    workflow.add_edge("writer", "storyboarder")

    # 分镜 -> 提示词生成
    workflow.add_edge("storyboarder", "prompter")

    # 提示词 -> 质量检查
    workflow.add_edge("prompter", "quality_checker")

    # 质量检查：通过则结束，否则返回提示词阶段重试
    workflow.add_conditional_edges(
        "quality_checker",
        route_after_quality,
        {
            "passed": END,
            "needs_revision": "prompter",
            "failed": END,
        }
    )

    # 使用内存检查点（也可替换为 AsyncPostgresSaver）
    memory = MemorySaver()

    # 编译工作流
    graph = workflow.compile(
        checkpointer=memory,
        interrupt_before=[],  # 可在 quality_checker 前插入人工审核
    )

    return graph


# ============ 路由函数 ============

def route_after_planning(state: MangaState) -> str:
    """策划结束后路由"""
    if state.get("error"):
        logger.error(f"策划阶段失败: {state['error']}")
        return "failed"
    return "writer"


def route_after_quality(state: MangaState) -> str:
    """质量检查后路由"""
    if state.get("error"):
        logger.error(f"质量检查失败: {state['error']}")
        return "failed"

    if state.get("passed_quality"):
        logger.info("质量检查通过 ✅")
        return "passed"

    # 检查重试次数
    revision_count = len(state.get("revision_notes", []))
    if revision_count >= 3:
        logger.warning(f"已重试 {revision_count} 次，强制结束")
        return "passed"  # 强制通过避免死循环

    logger.info("需要修订，返回提示词阶段")
    return "needs_revision"


# ============ 工作流实例 ============

# 全局单例
manga_workflow = create_manga_workflow()