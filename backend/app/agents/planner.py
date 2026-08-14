"""
策划 Agent —— 课件模式重写
ChatPromptTemplate(04) + with_structured_output(06) + Pydantic + Tools(05) + RAG(10)
"""
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.core.config import settings

logger = logging.getLogger(__name__)

# ===== 课件06: Pydantic 结构化输出模型 =====
class Character(BaseModel):
    """角色信息"""
    name: str = Field(description="角色姓名")
    role: str = Field(description="角色定位：主角/配角/反派")
    personality: str = Field(description="性格特征")
    appearance: str = Field(description="外貌描述")
    background: str = Field(description="背景故事")
    traits: List[str] = Field(description="特质标签列表", default_factory=list)

class PlanningOutput(BaseModel):
    """策划输出 — 课件06: 结构化输出"""
    chapter_title: str = Field(description="章节标题，根据故事内容自动生成")
    world_setting: str = Field(description="世界观设定（时代背景、地理环境、文明程度、特殊规则）")
    central_conflict: str = Field(description="核心冲突")
    theme: str = Field(description="主题思想")
    target_audience: str = Field(description="目标受众")
    style_reference: str = Field(description="风格参考建议")
    characters: List[Character] = Field(description="角色列表")
    scenes: List[Dict[str, Any]] = Field(description="场景规划列表", default_factory=list)
    outline_suggestion: str = Field(description="剧情方向建议", default="")


# ===== 课件04: ChatPromptTemplate =====
PLANNING_SYSTEM_TEMPLATE = """你是一位专业的漫画/动漫策划专家。你的任务是：
1. 分析用户输入的故事创意，构建完整的世界观设定
2. 设计核心角色（主角、配角、反派）
3. 确定故事主题、核心冲突和目标受众
4. 提供风格参考建议

【知识参考】
以下是从知识库中检索到的相关参考资料，可以帮助你更好地进行策划：
{rag_context}

请严格按照要求输出结构化数据。"""

PLANNING_HUMAN_TEMPLATE = """## 故事创意
{story_input}

## 类型
{genre}

## 要求
请基于上述创意，构建一个完整的世界观和角色设定。
输出章节标题、世界观、核心冲突、主题、目标受众、风格参考、角色列表和场景规划。"""

planning_prompt = ChatPromptTemplate.from_messages([
    ("system", PLANNING_SYSTEM_TEMPLATE),
    ("human", PLANNING_HUMAN_TEMPLATE),
])


class PlanningAgent:
    """策划 Agent — 课件07: 智能体模式"""

    def __init__(self):
        # 课件02: 模型创建
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            temperature=0.8,
        )
        # 课件06: with_structured_output
        self.chain = planning_prompt | self.llm.with_structured_output(PlanningOutput)

    def _retrieve_rag_context(self, story_input: str) -> str:
        """课件10: 从 RAG 知识库中检索与故事相关的参考上下文"""
        try:
            from app.services.rag_service import rag_service
            import asyncio

            # 从故事输入中提取关键词进行检索
            query = story_input[:200] if story_input else "漫画策划参考"
            loop = asyncio.new_event_loop()
            try:
                results = loop.run_until_complete(
                    rag_service.retrieve_context(query=query, top_k=settings.RAG_TOP_K)
                )
            finally:
                loop.close()

            if not results:
                return "（无相关参考知识）"

            context_parts = []
            for i, r in enumerate(results):
                text = r.get("text", "")
                source = r.get("source_type", "unknown")
                if text:
                    context_parts.append(f"[参考{i+1}]({source}): {text[:300]}")

            if context_parts:
                return "\n\n".join(context_parts)
            return "（无相关参考知识）"
        except Exception as e:
            logger.warning(f"RAG 检索失败: {e}")
            return "（知识库暂不可用）"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行策划任务"""
        logger.info("🤖 [策划 Agent] 开始工作...")

        try:
            story_input = state.get("story_input", "")
            genre = state.get("genre", "fantasy")

            # 课件10: 获取 RAG 上下文
            rag_context = self._retrieve_rag_context(story_input)
            if rag_context and "无相关" not in rag_context and "不可用" not in rag_context:
                logger.info(f"📚 [课件10] RAG 检索到参考知识，已注入策划提示词")
            else:
                logger.info("📚 [课件10] RAG 未检索到相关知识，使用无参考模式")

            # 课件04+06: 使用 ChatPromptTemplate + with_structured_output
            result: PlanningOutput = self.chain.invoke({
                "story_input": story_input or "在一个充满奇幻色彩的世界里，少年踏上寻找真相的旅程",
                "genre": genre,
                "rag_context": rag_context,
            })

            return {
                "chapter_title": result.chapter_title,
                "world_setting": result.world_setting,
                "central_conflict": result.central_conflict,
                "theme": result.theme,
                "target_audience": result.target_audience,
                "style_reference": result.style_reference,
                "characters": [c.model_dump() for c in result.characters],
                "scenes": result.scenes,
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