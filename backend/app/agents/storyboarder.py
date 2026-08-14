"""
分镜 Agent —— 课件模式重写
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
class Panel(BaseModel):
    """分镜面板"""
    panel_number: int = Field(description="分镜编号")
    composition: str = Field(description="构图（如全景镜头、中景、特写等）")
    camera_angle: str = Field(description="镜头角度（如平视、仰视、俯视等）")
    description: str = Field(description="画面描述，20字以内")
    dialogue: str = Field(description="对话内容", default="")
    narration: str = Field(description="旁白", default="")
    transition: str = Field(description="转场方式", default="cut")

class StoryboardSceneOutput(BaseModel):
    """单个场景的分镜输出"""
    scene_number: int = Field(description="场景编号")
    panels: List[Panel] = Field(description="分镜列表")


# ===== 课件04: ChatPromptTemplate =====
STORYBOARD_SYSTEM_TEMPLATE = """你是一位专业的漫画分镜师。你的任务是：
1. 将剧本场景分解为具体的漫画分镜
2. 设计每个分镜的构图、角度和镜头语言
3. 安排对话气泡和文字位置
4. 确保分镜节奏流畅，视觉叙事清晰

构图和角度必须根据场景内容动态选择，确保多样性。
构图可选：全景镜头、中景、特写、双人镜头、广角、远景、过肩镜头
角度可选：平视、仰视、俯视、低角度、过肩镜头、俯瞰

请严格按照要求输出结构化数据。"""

STORYBOARD_HUMAN_TEMPLATE = """## 场景信息
- 场景编号: {scene_number}
- 地点: {location}
- 时间: {time}
- 摘要: {summary}
- 关键对话: {key_dialogue}

## 角色外观参考
{character_desc}

## 要求
请为这个场景设计 {panel_count} 个分镜面板，每个面板描述一个镜头。
构图和角度必须根据场景内容动态选择，确保多样性和叙事流畅性。"""


class StoryboardAgent:
    """分镜 Agent — 课件07: 智能体模式"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            temperature=0.7,
        )
        # 课件06: with_structured_output
        self.chain = StoryboardSceneOutput  # 用于类型提示

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行分镜任务"""
        logger.info("🎨 [分镜 Agent] 开始分镜设计...")

        try:
            script = state.get("script", {})
            scenes = script.get("scenes", [])
            story_input = state.get("story_input", "")

            if not scenes:
                logger.warning("剧本中没有场景数据，使用故事输入生成默认场景")
                if story_input:
                    import re
                    segments = re.split(r'[。！？\n]', story_input.strip())
                    segments = [s.strip() for s in segments if len(s.strip()) > 5]
                    scenes = []
                    for i, seg in enumerate(segments[:5]):
                        scenes.append({
                            "scene_number": i + 1,
                            "summary": seg[:200],
                            "location": "未指定",
                            "time": "未指定",
                        })
                if not scenes:
                    scenes = [{"scene_number": 1, "summary": script.get("content", "")[:200]}]

            characters = state.get("characters", [])
            char_desc = "\n".join([
                f"- {c.get('name')}: {c.get('appearance', '')}"
                for c in characters
            ]) or "无角色信息"

            all_storyboards = []
            prompt_list = []  # 课件02: batch 批量处理
            scene_inputs = []

            for scene in scenes:
                summary = scene.get('summary', '') or scene.get('content', '')
                if len(summary) > 100:
                    panel_count = "4-6"
                elif len(summary) > 50:
                    panel_count = "3-5"
                else:
                    panel_count = "2-4"

                # 课件04: 构建 ChatPromptTemplate
                scene_prompt = ChatPromptTemplate.from_messages([
                    ("system", STORYBOARD_SYSTEM_TEMPLATE),
                    ("human", STORYBOARD_HUMAN_TEMPLATE),
                ])
                chain = scene_prompt | self.llm.with_structured_output(StoryboardSceneOutput)

                scene_inputs.append({
                    "scene_number": scene.get("scene_number", 1),
                    "location": scene.get("location", "未指定"),
                    "time": scene.get("time", "未指定"),
                    "summary": summary,
                    "key_dialogue": scene.get("dialogue", "") or scene.get("key_dialogue", ""),
                    "character_desc": char_desc,
                    "panel_count": panel_count,
                })
                prompt_list.append(chain)

            # 课件02: 使用 batch 并行处理多个场景
            results = [chain.invoke(inp) for chain, inp in zip(prompt_list, scene_inputs)]

            for result in results:
                if result:
                    for panel in result.panels:
                        all_storyboards.append({
                            "scene_number": result.scene_number,
                            "panel_number": panel.panel_number,
                            "composition": panel.composition,
                            "camera_angle": panel.camera_angle,
                            "description": panel.description,
                            "dialogue": panel.dialogue,
                            "prompt": f"anime style, {panel.composition}, {panel.camera_angle}, {panel.description}, cinematic lighting, 4k",
                        })

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