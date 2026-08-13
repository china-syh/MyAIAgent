"""
提示词 Agent - 将分镜转换为 AI 绘图提示词
"""
import logging
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一位专业的 AI 绘画提示词工程师。你的任务是：
1. 将每个分镜描述转换为高质量的 AI 绘图提示词（英文）
2. 提示词需要包含：构图、角色姿态、表情、背景、光影、色彩、风格
3. 参考角色设定确保一致性
4. 每个提示词应包含正向提示词和反向提示词

请输出结构化的 JSON 格式结果，包含：
- panels: 分镜提示词列表（每个包含 panel_number、positive_prompt、negative_prompt、style_params）"""


class PromptAgent:
    """提示词 Agent"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            temperature=0.6,
        )

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行提示词生成任务"""
        logger.info("🔧 [提示词 Agent] 生成绘图提示词...")

        try:
            storyboards = state.get("storyboards", [])
            characters = state.get("characters", [])
            style_ref = state.get("style_reference", "manga style")

            # 批量处理分镜
            all_prompts = []
            batch_size = 3  # 每批处理 3 个分镜

            for i in range(0, len(storyboards), batch_size):
                batch = storyboards[i:i + batch_size]
                prompt = self._build_batch_prompt(batch, characters, style_ref)
                response = self.llm.invoke([
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ])
                result = self._parse_response(response.content)
                all_prompts.extend(result.get("panels", []))

            return {
                "prompts": all_prompts,
                "status": "prompting_completed",
            }

        except Exception as e:
            logger.error(f"提示词 Agent 失败: {e}")
            return {
                "error": str(e),
                "error_count": state.get("error_count", 0) + 1,
                "status": "failed",
            }

    def _build_batch_prompt(
        self, batch: List[Dict[str, Any]], characters: List[Dict[str, Any]], style: str
    ) -> str:
        """构建批量提示词生成 prompt"""
        panels_desc = "\n---\n".join([
            f"Panel {p.get('panel_number', i + 1)} (Scene {p.get('scene_number', 1)}):\n"
            f"构图: {p.get('composition', '')}\n"
            f"角度: {p.get('camera_angle', '')}\n"
            f"描述: {p.get('description', '')}\n"
            f"对话: {p.get('dialogue', '')}"
            for i, p in enumerate(batch)
        ])

        char_desc = "\n".join([
            f"- {c.get('name')}: {c.get('appearance', '')}"
            for c in characters
        ])

        return f"""
## 分镜信息
{panels_desc}

## 角色外观
{char_desc}

## 风格
{style}

## 要求
为每个分镜生成英文 AI 绘图提示词，包含正向提示词和反向提示词。
输出 JSON 格式，包含 panels 数组。
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
            return {"panels": []}