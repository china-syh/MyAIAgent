"""
pytest 测试配置与共享 fixtures

提供测试用的数据库会话、HTTP 客户端、测试用户和项目等 fixtures。
使用 SQLite 内存数据库避免对 PostgreSQL 的依赖。
"""

import uuid
import asyncio
from typing import AsyncGenerator
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import String, TypeDecorator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy.pool import StaticPool

# ---------------------------------------------------------------------------
# SQLite 兼容的 UUID 类型（替换 PostgreSQL UUID）
# 必须在模型导入之前完成替换，确保模型使用自定义 UUID 类型
# ---------------------------------------------------------------------------

class _SQLiteUUID(TypeDecorator):
    """跨平台 UUID 类型，在 SQLite 上将 UUID 存储为字符串。"""
    impl = String(36)
    cache_ok = True

    def __init__(self, as_uuid: bool = True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.as_uuid = as_uuid

    def process_bind_param(self, value, dialect):
        if value is not None:
            if isinstance(value, uuid.UUID):
                return str(value)
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and self.as_uuid:
            return uuid.UUID(value)
        return value

    def coerce_compared_value(self, op, value):
        if isinstance(value, str):
            return String(36)
        return self


# 替换 PostgreSQL UUID 为 SQLite 兼容实现
import sqlalchemy.dialects.postgresql as _pg
_pg.UUID = _SQLiteUUID

# ---------------------------------------------------------------------------
# 测试数据库引擎和会话
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite://"

engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

TestSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """为整个测试会话创建一个事件循环。"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """每个测试函数前自动创建表，测试结束后销毁。"""
    from app.models.base import Base
    import app.models.user      # noqa: F401 确保模型被注册
    import app.models.project   # noqa: F401
    import app.models.audit_log # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ---------------------------------------------------------------------------
# 共享 Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """提供一个独立的数据库会话，测试结束后回滚。"""
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """FastAPI 测试客户端，使用 TestSessionLocal 覆盖 get_db 依赖。"""
    from app.main import app
    from app.database import get_db

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> dict:
    """创建一个测试用户并返回用户信息。"""
    from app.core.security import get_password_hash
    from app.models.user import User

    user = User(
        id=uuid.uuid4(),
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpass123"),
        display_name="Test User",
        role="user",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "password": "testpass123",
    }


@pytest_asyncio.fixture
async def test_project(db_session: AsyncSession, test_user: dict) -> dict:
    """创建一个测试项目并返回项目信息。"""
    from app.models.project import Project

    project = Project(
        id=uuid.uuid4(),
        user_id=uuid.UUID(test_user["id"]),
        name="测试项目",
        description="这是一个测试项目",
        story_input="一个关于勇者斗恶龙的故事",
        genre="fantasy",
        status="draft",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        is_active=True,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return {
        "id": str(project.id),
        "name": project.name,
        "description": project.description,
        "story_input": project.story_input,
        "genre": project.genre,
        "status": project.status,
    }


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, test_user: dict) -> dict:
    """获取登录后的认证头。"""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": test_user["username"], "password": test_user["password"]},
    )
    data = response.json()
    token = data["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}