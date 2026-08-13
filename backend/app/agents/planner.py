"""
策划 Agent - 负责故事世界观构建、角色设定
"""
import logging
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一位专业的漫画/动漫策划专家。你的任务是：
1. 分析用户输入的故事创意，构建完整的世界观设定
2. 设计核心角色（主角、配角、反派）
3. 确定故事主题、核心冲突和目标受众
4. 提供风格参考建议

请输出结构化的 JSON 格式结果，包含：
- world_setting: 世界观设定（时代背景、地理环境、文明程度、特殊规则）
- central_conflict: 核心冲突
- theme: 主题思想
- target_audience: 目标受众
- style_reference: 风格参考
- characters: 角色列表（每个角色包含 name, role, personality, appearance, background, traits）
- outline_suggestion: 剧情方向建议"""


class PlanningAgent:
    """策划 Agent"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            temperature=0.8,
        )

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行策划任务"""
        logger.info("🤖 [策划 Agent] 开始工作...")

        try:
            story_input = state.get("story_input", "")
            genre = state.get("genre", "fantasy")

            user_prompt = f"""
## 故事创意
{story_input}

## 类型
{genre}

## 要求
请基于上述创意，构建一个完整的世界观和角色设定。
输出必须为 JSON 格式，包含 world_setting、central_conflict、theme、target_audience、style_reference、characters 等字段。
"""

            response = self.llm.invoke([
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ])

            # 解析 LLM 输出
            result = self._parse_response(response.content)

            return {
                "world_setting": result.get("world_setting", {}),
                "central_conflict": result.get("central_conflict", ""),
                "theme": result.get("theme", ""),
                "target_audience": result.get("target_audience", ""),
                "style_reference": result.get("style_reference", ""),
                "characters": result.get("characters", []),
                "status": "planning_completed",
                "needs_human_approval": False,
            }

        except Exception as e:
            logger.error(f"策划 Agent 失败: {e}")
            return {
                "error": str(e),
                "error_count": state.get("error_count", 0) + 1,
                "status": "failed",
            }

    def _parse_response(self, content: str) -> dict:
        """解析 LLM 响应为 JSON"""
        import json
        import re

        # 尝试提取 JSON 块
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 直接尝试解析
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.warning("无法解析 LLM 响应为 JSON，返回原始内容")
            return {"raw_response": content}