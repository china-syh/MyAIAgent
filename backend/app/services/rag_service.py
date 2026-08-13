"""
RAG 检索服务 - 增强的语义检索
"""
import logging
from typing import List, Dict, Any, Optional
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings
from app.services.milvus_service import milvus_service

logger = logging.getLogger(__name__)


class RagService:
    """RAG 检索服务"""

    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )

    async def get_embedding(self, text: str) -> List[float]:
        """获取文本向量"""
        return await self.embeddings.aembed_query(text)

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """批量获取文本向量"""
        return await self.embeddings.aembed_documents(texts)

    async def store_knowledge(
        self,
        texts: List[str],
        source_type: str,
        project_id: str,
        metadata: Optional[List[Dict]] = None,
    ):
        """存储知识到 Milvus"""
        embeddings = await self.get_embeddings(texts)
        await milvus_service.insert_knowledge(
            texts=texts,
            embeddings=embeddings,
            source_type=source_type,
            project_id=project_id,
            metadata=metadata,
        )

    async def retrieve_context(
        self,
        query: str,
        project_id: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """检索相关上下文"""
        query_embedding = await self.get_embedding(query)
        results = await milvus_service.search_similar(
            embedding=query_embedding,
            top_k=top_k,
            project_id=project_id,
        )
        return results

    async def build_rag_context(
        self,
        query: str,
        project_id: Optional[str] = None,
        max_tokens: int = 2000,
    ) -> str:
        """构建 RAG 上下文文本"""
        results = await self.retrieve_context(query, project_id)
        if not results:
            return ""

        context_parts = []
        for i, r in enumerate(results):
            context_parts.append(f"[参考 {i + 1}] {r['text']}")

        return "\n\n".join(context_parts)


# 全局单例
rag_service = RagService()