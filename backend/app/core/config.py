from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    # 应用
    APP_NAME: str = "AI 漫剧 Agent"
    APP_VERSION: str = "2.0.0"
    ENV: str = "development"
    DEBUG: bool = True

    # 安全
    SECRET_KEY: str = "manga-agent-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    ALLOWED_HOSTS: List[str] = ["*"]

    # 数据库
    DATABASE_URL: str = "postgresql+asyncpg://manga:manga123@localhost:5432/manga_agent"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Milvus (RAG 向量存储 — 课件10)
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_ALIAS: str = "default"

    # ===== 课件02: LLM 模型配置 =====
    LLM_PROVIDER: str = "deepseek"
    OPENAI_API_KEY: str = "sk-your-api-key"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"

    # ===== DeepSeek =====
    DEEPSEEK_API_KEY: str = "sk-your-deepseek-api-key"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # ===== 课件03: LangSmith 追踪配置 =====
    LANGSMITH_TRACING: bool = False
    LANGSMITH_API_KEY: Optional[str] = None
    LANGSMITH_PROJECT: str = "ai-manga-agent"
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"

    # ===== 课件06: 结构化输出 =====
    STRUCTURED_OUTPUT_MODEL: str = ""

    # Image generation provider
    IMAGE_PROVIDER: str = "pollinations"
    IMAGE_API_URL: str = "https://image.pollinations.ai/prompt"
    IMAGE_MODEL: str = "flux"
    HF_TOKEN: str = ""
    HF_IMAGE_MODEL: str = "black-forest-labs/FLUX.1-schnell"
    IMAGE_TIMEOUT_SECONDS: int = 90
    IMAGE_RETRIES: int = 3

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # 向量
    EMBEDDING_DIM: int = 1536
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # ===== 课件10: RAG 配置 =====
    RAG_CHUNK_SIZE: int = 500
    RAG_CHUNK_OVERLAP: int = 50
    RAG_DOC_LOADER: str = "pdf"
    RAG_TOP_K: int = 3
    RAG_COLLECTION_NAME: str = "manga_knowledge"

    # 文件上传
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024
    ALLOWED_EXTENSIONS: List[str] = ["jpg", "jpeg", "png", "gif", "webp", "pdf"]

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:3000",
        "http://localhost:80",
    ]

    @property
    def cors_args(self) -> dict:
        return {
            "allow_origins": self.CORS_ORIGINS,
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        }

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()