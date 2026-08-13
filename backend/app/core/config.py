from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # 应用
    APP_NAME: str = "AI 漫剧 Agent"
    APP_VERSION: str = "2.0.0"
    ENV: str = "development"  # development / staging / production
    DEBUG: bool = True

    # 安全
    SECRET_KEY: str = "manga-agent-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24小时
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    ALLOWED_HOSTS: List[str] = ["*"]

    # 数据库
    DATABASE_URL: str = "postgresql+asyncpg://manga:manga123@localhost:5432/manga_agent"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Milvus
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_ALIAS: str = "default"

    # LLM
    OPENAI_API_KEY: str = "sk-your-api-key"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # DeepSeek
    DEEPSEEK_API_KEY: str = "sk-your-deepseek-api-key"  # 请在 .env 中设置
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"

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

    # 文件上传
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
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
