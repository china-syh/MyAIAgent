"""
LangChain Tools 模块 —— 课件05: Tools 定义
MCP 风格工具封装，每个工具包含 name, description, args_schema
"""
import logging
import httpx
import json
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool, StructuredTool
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings

logger = logging.getLogger(__name__)


# ===== 工具输入 Schema（课件05: args_schema） =====

class RAGRetrieveInput(BaseModel):
    """RAG 知识检索工具输入"""
    query: str = Field(description="检索查询文本")
    project_id: Optional[str] = Field(default=None, description="项目ID，用于限定检索范围")
    top_k: int = Field(default=3, description="返回结果数量")


class ImageGenerateInput(BaseModel):
    """图片生成工具输入"""
    prompt: str = Field(description="图片生成提示词（英文）")
    width: int = Field(default=1024, description="图片宽度")
    height: int = Field(default=1024, description="图片高度")


class StoryAnalyzeInput(BaseModel):
    """故事分析工具输入"""
    story_text: str = Field(description="故事文本")
    analysis_type: str = Field(default="characters", description="分析类型: characters/scenes/themes")


class KnowledgeSearchInput(BaseModel):
    """知识库搜索工具输入"""
    query: str = Field(description="搜索关键词")
    source_type: Optional[str] = Field(default=None, description="知识来源类型过滤")


# ===== 工具定义（课件05: StructuredTool） =====

def rag_retrieve(query: str, project_id: Optional[str] = None, top_k: int = 3) -> str:
    """RAG 知识检索 —— 从 Milvus 向量库中检索与 query 相关的知识上下文"""
    try:
        from app.services.rag_service import rag_service
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            results = loop.run_until_complete(
                rag_service.retrieve_context(query=query, project_id=project_id, top_k=top_k)
            )
        finally:
            loop.close()

        if not results:
            return "未检索到相关知识。"

        context_parts = []
        for i, r in enumerate(results):
            text = r.get("text", "")
            score = r.get("score", 0)
            source = r.get("source_type", "unknown")
            context_parts.append(f"[参考 {i+1}] (来源: {source}, 相关度: {score:.2f})\n{text}")

        return "\n\n".join(context_parts)
    except Exception as e:
        logger.warning(f"RAG 检索失败: {e}")
        return f"RAG 检索不可用: {e}"


def image_generate(prompt: str, width: int = 1024, height: int = 1024) -> str:
    """图片生成 —— 调用 Pollinations API 生成图片"""
    try:
        url = f"{settings.IMAGE_API_URL}/{prompt}"
        params = {
            "width": width,
            "height": height,
            "model": settings.IMAGE_MODEL,
        }
        response = httpx.get(url, params=params, timeout=settings.IMAGE_TIMEOUT_SECONDS)
        if response.status_code == 200:
            return f"图片生成成功: {response.url}"
        else:
            return f"图片生成失败: HTTP {response.status_code}"
    except Exception as e:
        return f"图片生成出错: {e}"


def story_analyze(story_text: str, analysis_type: str = "characters") -> str:
    """故事分析 —— 分析故事文本中的角色、场景或主题"""
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate

    llm = ChatOpenAI(
        model=settings.LLM_MODEL,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        temperature=0.3,
    )

    templates = {
        "characters": "分析以下故事文本中的角色，提取每个角色的：姓名、角色定位、性格特征。\n\n故事：{text}",
        "scenes": "分析以下故事文本中的场景，列出每个场景的：地点、时间、主要事件。\n\n故事：{text}",
        "themes": "分析以下故事文本的主题思想，列出核心主题和情感基调。\n\n故事：{text}",
    }

    prompt_text = templates.get(analysis_type, templates["characters"])
    prompt = ChatPromptTemplate.from_messages([("human", prompt_text)])
    chain = prompt | llm
    result = chain.invoke({"text": story_text[:2000]})
    return result.content


def knowledge_search(query: str, source_type: Optional[str] = None) -> str:
    """知识库搜索 —— 搜索本地知识库中的漫画/动漫相关参考资料"""
    try:
        from app.services.rag_service import rag_service
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            results = loop.run_until_complete(
                rag_service.retrieve_context(query=query, top_k=5)
            )
        finally:
            loop.close()

        if not results:
            return "未找到相关参考资料。"

        # 按来源类型过滤
        if source_type:
            results = [r for r in results if r.get("source_type") == source_type]

        if not results:
            return f"未找到来源类型为 '{source_type}' 的参考资料。"

        parts = []
        for r in results:
            parts.append(f"- {r.get('text', '')[:200]}")
        return "\n".join(parts)
    except Exception as e:
        return f"知识库搜索不可用: {e}"


# ===== 课件05: 工具注册 =====
def get_available_tools() -> List[StructuredTool]:
    """获取所有可用工具列表 —— 供 Agent 使用"""
    tools = [
        StructuredTool(
            name="rag_retrieve",
            description="从知识库中检索与查询相关的上下文信息，用于增强故事创作的知识背景",
            func=rag_retrieve,
            args_schema=RAGRetrieveInput,
        ),
        StructuredTool(
            name="image_generate",
            description="根据提示词生成图片，用于生成漫画分镜画面",
            func=image_generate,
            args_schema=ImageGenerateInput,
        ),
        StructuredTool(
            name="story_analyze",
            description="分析故事文本，提取角色、场景或主题信息",
            func=story_analyze,
            args_schema=StoryAnalyzeInput,
        ),
        StructuredTool(
            name="knowledge_search",
            description="搜索本地知识库中的漫画/动漫参考资料",
            func=knowledge_search,
            args_schema=KnowledgeSearchInput,
        ),
    ]
    return tools


# ===== 课件05: 绑定工具到 LLM =====
def bind_tools_to_llm(llm):
    """将工具绑定到 LLM —— 使 LLM 可以调用工具"""
    tools = get_available_tools()
    return llm.bind_tools(tools)