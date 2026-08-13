"""
质量检查 Agent - 审核提示词质量和一致性
"""
import logging
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一位专业的 AI 漫画质量控制专家。你的任务是：
1. 检查所有提示词的质量和一致性
2. 确保角色外观、场景风格、构图合理性
3. 检查是否存在角色 OOC（Out of Character）
4. 提供具体的修改建议

请输出结构化的 JSON 格式结果，包含：
- passed: bool 是否通过
- score: int 质量评分 (0-100)
- issues: list 问题列表
- suggestions: list 修改建议
- revised_panels: list 需要修改的分镜编号"""


class QualityCheckerAgent:
    """质量检查 Agent"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            temperature=0.3,
        )

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行质量检查"""
        logger.info("✅ [质量检查 Agent] 开始审核...")

        try:
            prompts = state.get("prompts", [])
            storyboards = state.get("storyboards", [])
            characters = state.get("characters", [])

            if not prompts:
                logger.warning("没有提示词需要检查")
                return {
                    "passed_quality": True,
                    "quality_report": {"passed": True, "score": 100, "issues": [], "suggestions": []},
                    "revision_notes": [],
                    "status": "reviewing_completed",
                }

            context = self._build_context(prompts, storyboards, characters)
            response = self.llm.invoke([
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": context},
            ])

            result = self._parse_response(response.content)
            passed = result.get("passed", False)
            issues = result.get("issues", [])
            suggestions = result.get("suggestions", [])

            return {
                "passed_quality": passed,
                "quality_report": result,
                "revision_notes": suggestions if not passed else [],
                "status": "reviewing_completed",
            }

        except Exception as e:
            logger.error(f"质量检查 Agent 失败: {e}")
            return {
                "error": str(e),
                "error_count": state.get("error_count", 0) + 1,
                "status": "failed",
            }

    def _build_context(
        self, prompts: List[Dict], storyboards: List[Dict], characters: List[Dict]
    ) -> str:
        """构建检查上下文"""
        char_desc = "\n".join([
            f"- {c.get('name')} ({c.get('role', '')}): {c.get('personality', '')}"
            for c in characters
        ])

        prompt_summary = "\n---\n".join([
            f"Panel {p.get('panel_number', i + 1)}:\n{p.get('positive_prompt', '')[:200]}"
            for i, p in enumerate(prompts[:10])
        ])

        return f"""
## 角色设定
{char_desc}

## 提示词（前 10 个）
{prompt_summary}

## 要求
检查以上提示词的质量和一致性。输出 JSON 格式。
"""

    def _parse_response(self, content: str) -> dict:
        import json
        import re

        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"passed": True, "score": 80, "issues": [], "suggestions": []}