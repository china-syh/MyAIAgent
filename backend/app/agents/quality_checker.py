"""
质量检查 Agent —— 课件模式重写
ChatPromptTemplate(04) + with_structured_output(06) + Pydantic
"""
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.core.config import settings

logger = logging.getLogger(__name__)


# ===== 课件06: Pydantic 结构化输出 =====
class QualityReport(BaseModel):
    """质量检查报告"""
    passed: bool = Field(description="是否通过质量检查")
    score: int = Field(description="质量评分（0-100）", ge=0, le=100)
    issues: List[str] = Field(description="问题列表", default_factory=list)
    suggestions: List[str] = Field(description="改进建议", default_factory=list)
    revised_panels: List[int] = Field(description="需要修改的分镜编号", default_factory=list)


# ===== 课件04: ChatPromptTemplate =====
QUALITY_SYSTEM_TEMPLATE = """你是一个漫画质量控制专家。你的任务是：
1. 检查分镜与剧本的一致性
2. 评估提示词的质量和有效性
3. 检查角色外观的一致性
4. 提供具体的改进建议

请严格按照要求输出结构化数据。"""

QUALITY_HUMAN_TEMPLATE = """## 剧本场景数
{scene_count}

## 分镜数
{storyboard_count}

## 提示词数
{prompt_count}

## 角色数
{character_count}

## 故事类型
{story_input_preview}

## 要求
请评估以上内容的质量，从完整性和一致性角度给出评分和问题列表。"""


class QualityCheckerAgent:
    """质量检查 Agent — 课件07: 智能体模式"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            temperature=0.3,
        )
        self.chain = ChatPromptTemplate.from_messages([
            ("system", QUALITY_SYSTEM_TEMPLATE),
            ("human", QUALITY_HUMAN_TEMPLATE),
        ]) | self.llm.with_structured_output(QualityReport)

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行质量检查"""
        logger.info("✅ [质量检查 Agent] 检查内容质量...")

        try:
            script = state.get("script", {})
            scenes = script.get("scenes", []) if script else []
            storyboards = state.get("storyboards", [])
            prompts = state.get("prompts", [])
            characters = state.get("characters", [])
            story_input = state.get("story_input", "")

            # 空数据检查 — 直接通过
            if not prompts or not storyboards:
                return {
                    "passed_quality": True,
                    "quality_report": {
                        "passed": True, "score": 100,
                        "issues": [], "suggestions": [],
                    },
                    "revision_notes": [],
                    "status": "reviewing_completed",
                }

            # 课件04+06: ChatPromptTemplate + with_structured_output
            result: QualityReport = self.chain.invoke({
                "scene_count": len(scenes),
                "storyboard_count": len(storyboards),
                "prompt_count": len(prompts),
                "character_count": len(characters),
                "story_input_preview": story_input[:50] if story_input else "未提供",
            })

            return {
                "passed_quality": result.passed,
                "quality_report": result.model_dump(),
                "revision_notes": [
                    f"面板 {pn}: 需要修改" for pn in result.revised_panels
                ],
                "status": "reviewing_completed",
            }

        except Exception as e:
            logger.error(f"质量检查 Agent 失败: {e}")
            return {
                "error": str(e),
                "error_count": state.get("error_count", 0) + 1,
                "status": "failed",
            }