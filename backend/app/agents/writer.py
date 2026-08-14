"""
编剧 Agent —— 课件模式重写
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
class Scene(BaseModel):
    """场景"""
    scene_number: int = Field(description="场景编号")
    title: str = Field(description="场景标题")
    content: str = Field(description="场景描述，50字以内")
    dialogue: str = Field(description="关键对话", default="")

class ScriptOutput(BaseModel):
    """剧本输出"""
    chapter_number: int = Field(description="章节编号")
    title: str = Field(description="章节标题")
    outline: str = Field(description="章节大纲")
    scenes: List[Scene] = Field(description="场景列表")
    content: str = Field(description="完整剧本内容")


# ===== 课件04: ChatPromptTemplate =====
WRITING_SYSTEM_TEMPLATE = """你是一个专业的漫画剧本作家。你的任务是：
1. 根据故事策划方案，创作完整的剧本内容
2. 设计场景转折和节奏
3. 撰写对话和旁白
4. 确保剧情连贯、情感饱满

请严格按照要求输出结构化数据。"""

WRITING_HUMAN_TEMPLATE = """## 故事内容
{story_input}

## 世界观设定
{world_setting}

## 核心冲突
{central_conflict}

## 主题
{theme}

## 角色
{character_desc}

## 风格参考
{style_reference}

## 场景规划
{scene_desc}

## 要求
请基于以上信息，创作完整的剧本。
为每个场景设计标题、内容描述和关键对话，确保剧情连贯。"""

writing_prompt = ChatPromptTemplate.from_messages([
    ("system", WRITING_SYSTEM_TEMPLATE),
    ("human", WRITING_HUMAN_TEMPLATE),
])


class WritingAgent:
    """编剧 Agent — 课件07: 智能体模式"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            temperature=0.9,
        )
        # 课件06: with_structured_output
        self.chain = writing_prompt | self.llm.with_structured_output(ScriptOutput)

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行编剧任务"""
        logger.info("✍️ [编剧 Agent] 开始创作剧本...")

        try:
            # 构建输入
            characters = state.get("characters", [])
            char_desc = "\n".join([
                f"- {c.get('name')}({c.get('role', '')}): {c.get('personality', '')}"
                for c in characters
            ]) or "无角色信息"

            scenes = state.get("scenes", [])
            scene_desc = "\n".join([
                f"场景{s.get('scene_number')}：{s.get('description', '')}"
                for s in scenes
            ]) or "无场景规划"

            # 课件04+06: 使用 ChatPromptTemplate + with_structured_output
            result: ScriptOutput = self.chain.invoke({
                "story_input": state.get("story_input", ""),
                "world_setting": state.get("world_setting", ""),
                "central_conflict": state.get("central_conflict", ""),
                "theme": state.get("theme", ""),
                "character_desc": char_desc,
                "style_reference": state.get("style_reference", ""),
                "scene_desc": scene_desc,
            })

            return {
                "script": {
                    "chapter_number": result.chapter_number,
                    "title": result.title,
                    "outline": result.outline,
                    "scenes": [s.model_dump() for s in result.scenes],
                    "content": result.content,
                },
                "status": "writing_completed",
            }

        except Exception as e:
            logger.error(f"编剧 Agent 失败: {e}")
            return {
                "error": str(e),
                "error_count": state.get("error_count", 0) + 1,
                "status": "failed",
            }