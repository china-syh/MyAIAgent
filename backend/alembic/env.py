"""
Alembic 迁移环境配置

使用 SQLAlchemy async engine，支持自动迁移生成。
"""

import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

# 将项目根目录加入 sys.path，确保可导入 app 模块
sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)

# Alembic Config 对象，获取 alembic.ini 中的值
config = context.config

# 日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 导入所有模型，确保 Base.metadata 完整
from app.models.base import Base  # noqa: E402
import app.models.user  # noqa: E402, F401
import app.models.project  # noqa: E402, F401
import app.models.audit_log  # noqa: E402, F401

# 设置 target_metadata，供自动迁移使用
target_metadata = Base.metadata

# 其他元数据配置（用于不使用的数据库，此处留空）
# 若需处理多个数据库，可在此添加


def get_url() -> str:
    """获取数据库 URL。

    优先使用环境变量 ALEMBIC_DATABASE_URL，
    否则从 app.core.config.settings 获取。
    """
    url = os.getenv("ALEMBIC_DATABASE_URL")
    if url:
        return url
    from app.core.config import settings  # noqa: E402

    return settings.DATABASE_URL


def run_migrations_offline() -> None:
    """离线模式运行迁移。

    此模式下只生成 SQL 脚本，不连接数据库。
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # 比较列类型变化
        compare_server_default=True,  # 比较默认值变化
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """在连接上执行迁移。"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """在线模式运行迁移，使用 async engine。"""
    url = get_url()
    # 确保 URL 使用 async 驱动
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql+psycopg2://"):
        url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(url, poolclass=pool.NullPool)

    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await engine.dispose()


def run_migrations_online() -> None:
    """在线模式运行迁移。"""
    asyncio.run(run_async_migrations())


# 根据上下文选择迁移模式
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()