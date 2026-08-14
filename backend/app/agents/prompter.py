"""
提示词 Agent —— 课件模式重写
ChatPromptTemplate(04) + with_structured_output(06) + Pydantic + batch(02)
"""
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.core.config import settings

logger = logging.getLogger(__name__)


# ===== 课件06: Pydantic 结构化输出 =====
class PanelPrompt(BaseModel):
    """分镜提示词"""
    panel_number: int = Field(description="分镜编号")
    scene_number: int = Field(description="场景编号")
    positive_prompt: str = Field(description="正向提示词（英文）")
    negative_prompt: str = Field(description="反向提示词", default="")
    style_params: Dict[str, Any] = Field(description="风格参数", default_factory=dict)

class PromptOutput(BaseModel):
    """提示词输出"""
    panels: List[PanelPrompt] = Field(description="分镜提示词列表")


# ===== 课件04: ChatPromptTemplate =====
PROMPT_SYSTEM_TEMPLATE = """你是一位专业的 AI 绘画提示词工程师。你的任务是：
1. 将每个分镜描述转换为高质量的 AI 绘图提示词（英文）
2. 提示词需要包含：构图、角色姿态、表情、背景、光影、色彩、风格
3. 参考角色设定确保一致性
4. 每个提示词应包含正向提示词和反向提示词

请严格按照要求输出结构化数据。"""

PROMPT_HUMAN_TEMPLATE = """## 分镜信息
{panels_desc}

## 角色外观
{char_desc}

## 风格
{style}

## 要求
为每个分镜生成英文 AI 绘图提示词，包含正向提示词和反向提示词。
提示词必须与分镜的构图、角度、描述高度匹配。"""


class PromptAgent:
    """提示词 Agent — 课件07: 智能体模式"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            temperature=0.6,
        )
        # 课件06: with_structured_output
        self.chain = ChatPromptTemplate.from_messages([
            ("system", PROMPT_SYSTEM_TEMPLATE),
            ("human", PROMPT_HUMAN_TEMPLATE),
        ]) | self.llm.with_structured_output(PromptOutput)

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行提示词生成任务"""
        logger.info("🔧 [提示词 Agent] 生成绘图提示词...")

        try:
            storyboards = state.get("storyboards", [])
            characters = state.get("characters", [])
            story_input = state.get("story_input", "")

            # 根据故事内容动态确定风格
            style_ref = state.get("style_reference", "")
            if not style_ref and story_input:
                story_lower = story_input.lower()
                if any(kw in story_lower for kw in ["科幻", "未来", "赛博", "宇宙"]):
                    style_ref = "sci-fi anime style, futuristic"
                elif any(kw in story_lower for kw in ["奇幻", "魔法", "龙", "精灵"]):
                    style_ref = "fantasy anime style, magical"
                elif any(kw in story_lower for kw in ["恐怖", "悬疑", "惊悚", "黑暗"]):
                    style_ref = "dark anime style, horror atmosphere"
                elif any(kw in story_lower for kw in ["校园", "日常", "青春"]):
                    style_ref = "slice of life anime style, bright"
                elif any(kw in story_lower for kw in ["武侠", "功夫", "古代"]):
                    style_ref = "wuxia anime style, traditional ink painting"
                elif any(kw in story_lower for kw in ["战争", "历史", "战国"]):
                    style_ref = "epic anime style, realistic"
                else:
                    style_ref = "manga style, anime"
            else:
                style_ref = state.get("style_reference", "manga style, anime")

            if not storyboards:
                return {"prompts": [], "status": "prompting_completed"}

            char_desc = "\n".join([
                f"- {c.get('name')}: {c.get('appearance', '')}"
                for c in characters
            ]) or "无角色信息"

            # 根据分镜数量动态调整批处理
            total_panels = len(storyboards)
            batch_size = total_panels if total_panels <= 4 else (4 if total_panels <= 8 else 3)

            all_prompts = []
            for i in range(0, len(storyboards), batch_size):
                batch = storyboards[i:i + batch_size]
                panels_desc = "\n---\n".join([
                    f"Panel {p.get('panel_number', i + 1)} (Scene {p.get('scene_number', 1)}):\n"
                    f"构图: {p.get('composition', '')}\n"
                    f"角度: {p.get('camera_angle', '')}\n"
                    f"描述: {p.get('description', '')}\n"
                    f"对话: {p.get('dialogue', '')}"
                    for i, p in enumerate(batch)
                ])

                # 课件04+06: ChatPromptTemplate + with_structured_output
                result: PromptOutput = self.chain.invoke({
                    "panels_desc": panels_desc,
                    "char_desc": char_desc,
                    "style": style_ref,
                })
                all_prompts.extend([p.model_dump() for p in result.panels])

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