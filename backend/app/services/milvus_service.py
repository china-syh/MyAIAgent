"""
Milvus 向量数据库服务 - 知识库检索与存储
"""
import logging
from typing import List, Dict, Any, Optional
from pymilvus import (
    connections, Collection, CollectionSchema,
    FieldSchema, DataType, utility
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class MilvusService:
    """Milvus 向量数据库服务"""

    def __init__(self):
        self.collection_name = "manga_knowledge"
        self.dim = settings.EMBEDDING_DIM
        self._connected = False

    async def connect(self):
        """连接 Milvus"""
        if self._connected:
            return

        try:
            connections.connect(
                alias=settings.MILVUS_ALIAS,
                host=settings.MILVUS_HOST,
                port=settings.MILVUS_PORT,
            )
            self._ensure_collection()
            self._connected = True
            logger.info("✅ Milvus 连接成功")
        except Exception as e:
            logger.warning(f"Milvus 连接失败: {e}，将使用降级模式")
            self._connected = False

    def _ensure_collection(self):
        """确保集合存在"""
        if utility.has_collection(self.collection_name):
            self.collection = Collection(self.collection_name)
            return

        # 创建集合
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dim),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="metadata", dtype=DataType.JSON),
            FieldSchema(name="source_type", dtype=DataType.VARCHAR, max_length=50),
            FieldSchema(name="project_id", dtype=DataType.VARCHAR, max_length=50),
        ]
        schema = CollectionSchema(fields, description="AI 漫剧知识库")
        self.collection = Collection(self.collection_name, schema)

        # 创建索引
        index_params = {
            "metric_type": "IP",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128},
        }
        self.collection.create_index("embedding", index_params)
        logger.info(f"✅ 创建 Milvus 集合: {self.collection_name}")

    async def insert_knowledge(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        source_type: str,
        project_id: str,
        metadata: Optional[List[Dict]] = None,
    ):
        """插入知识向量"""
        if not self._connected:
            logger.warning("Milvus 未连接，跳过插入")
            return

        if metadata is None:
            metadata = [{} for _ in texts]

        entities = [
            [embeddings],
            texts,
            metadata,
            [source_type] * len(texts),
            [project_id] * len(texts),
        ]
        self.collection.insert(entities)
        self.collection.flush()
        logger.info(f"✅ 插入 {len(texts)} 条知识向量")

    async def search_similar(
        self,
        embedding: List[float],
        top_k: int = 5,
        project_id: Optional[str] = None,
        source_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """检索相似知识"""
        if not self._connected:
            logger.warning("Milvus 未连接，返回空结果")
            return []

        self.collection.load()

        # 构建过滤条件
        expr = None
        filters = []
        if project_id:
            filters.append(f'project_id == "{project_id}"')
        if source_type:
            filters.append(f'source_type == "{source_type}"')
        if filters:
            expr = " and ".join(filters)

        search_params = {
            "metric_type": "IP",
            "params": {"nprobe": 10},
        }

        results = self.collection.search(
            data=[embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=["text", "metadata", "source_type"],
        )

        retrieved = []
        for hits in results:
            for hit in hits:
                retrieved.append({
                    "id": hit.id,
                    "score": hit.score,
                    "text": hit.entity.get("text"),
                    "metadata": hit.entity.get("metadata"),
                    "source_type": hit.entity.get("source_type"),
                })

        return retrieved

    async def delete_by_project(self, project_id: str):
        """删除项目的所有知识"""
        if not self._connected:
            return
        self.collection.delete(f'project_id == "{project_id}"')

    def close(self):
        """关闭连接"""
        if self._connected:
            connections.disconnect(settings.MILVUS_ALIAS)
            self._connected = False


# 全局单例
milvus_service = MilvusService()