"""
编剧 Agent - 负责剧本创作
"""
import logging
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一位专业的漫画剧本作家。你的任务是：
1. 基于策划阶段的世界观和角色设定，创作完整的剧本
2. 设计剧情结构（起承转合）
3. 编写对话和场景描述
4. 确保剧情连贯且符合角色设定

请输出结构化的 JSON 格式结果，包含：
- chapter_number: 章节号
- title: 章节标题
- outline: 剧情大纲（起承转合各阶段）
- scenes: 场景列表（每个场景包含 scene_number、location、time、summary、characters_involved、key_dialogue）
- content: 完整的剧本正文"""


class WritingAgent:
    """编剧 Agent"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            temperature=0.9,
        )

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行编剧任务"""
        logger.info("✍️  [编剧 Agent] 开始创作...")

        try:
            # 构建上下文
            context = self._build_context(state)

            response = self.llm.invoke([
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": context},
            ])

            result = self._parse_response(response.content)

            return {
                "script": result,
                "script_outline": result.get("outline", []),
                "chapters": [result],
                "status": "writing_completed",
            }

        except Exception as e:
            logger.error(f"编剧 Agent 失败: {e}")
            return {
                "error": str(e),
                "error_count": state.get("error_count", 0) + 1,
                "status": "failed",
            }

    def _build_context(self, state: Dict[str, Any]) -> str:
        """构建编剧上下文"""
        world = state.get("world_setting", {})
        characters = state.get("characters", [])
        story_input = state.get("story_input", "")
        conflict = state.get("central_conflict", "")
        theme = state.get("theme", "")

        char_desc = "\n".join([
            f"- {c.get('name', '未知')} ({c.get('role', '')}): "
            f"性格={c.get('personality', '')}, 外貌={c.get('appearance', '')}"
            for c in characters
        ])

        return f"""
## 世界观
{world}

## 核心冲突
{conflict}

## 主题
{theme}

## 角色
{char_desc}

## 原始创意
{story_input}

## 要求
基于以上设定，创作第 1 章的完整剧本。输出 JSON 格式。
"""

    def _parse_response(self, content: str) -> dict:
        """解析 LLM 响应"""
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
            return {"raw_content": content, "scenes": []}