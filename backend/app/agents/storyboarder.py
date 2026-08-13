"""
分镜 Agent - 将剧本转换为分镜稿
"""
import logging
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一位专业的漫画分镜师。你的任务是：
1. 将剧本场景分解为具体的漫画分镜（panel）
2. 设计每个分镜的构图、角度和镜头语言
3. 安排对话气泡和文字位置
4. 确保分镜节奏流畅，视觉叙事清晰

请输出结构化的 JSON 格式结果，包含：
- scene_number: 场景编号
- panels: 分镜列表（每个 panel 包含 panel_number、composition、camera_angle、description、dialogue、narration、transition）"""


class StoryboardAgent:
    """分镜 Agent"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            temperature=0.7,
        )

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行分镜任务"""
        logger.info("🎨 [分镜 Agent] 开始分镜设计...")

        try:
            script = state.get("script", {})
            scenes = script.get("scenes", [])

            if not scenes:
                logger.warning("剧本中没有场景数据，使用默认场景")
                scenes = [{"scene_number": 1, "summary": script.get("content", "")[:200]}]

            all_storyboards = []
            for scene in scenes:
                scene_prompt = self._build_scene_prompt(scene, state)
                response = self.llm.invoke([
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": scene_prompt},
                ])
                result = self._parse_response(response.content)
                panels = result.get("panels", [])
                for panel in panels:
                    panel["scene_number"] = scene.get("scene_number", 1)
                all_storyboards.extend(panels)

            return {
                "storyboards": all_storyboards,
                "status": "storyboarding_completed",
            }

        except Exception as e:
            logger.error(f"分镜 Agent 失败: {e}")
            return {
                "error": str(e),
                "error_count": state.get("error_count", 0) + 1,
                "status": "failed",
            }

    def _build_scene_prompt(self, scene: Dict[str, Any], state: Dict[str, Any]) -> str:
        """构建分镜提示"""
        characters = state.get("characters", [])
        char_desc = "\n".join([
            f"- {c.get('name')}: {c.get('appearance', '')}"
            for c in characters
        ])

        return f"""
## 场景信息
- 场景编号: {scene.get('scene_number', 1)}
- 地点: {scene.get('location', '未指定')}
- 时间: {scene.get('time', '未指定')}
- 摘要: {scene.get('summary', '')}
- 关键对话: {scene.get('key_dialogue', '')}

## 角色外观参考
{char_desc}

## 要求
请为这个场景设计 3-6 个分镜面板，每个面板描述一个镜头。
输出 JSON 格式，包含 panels 数组。
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
            return {"panels": []}