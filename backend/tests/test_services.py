"""
服务层测试

测试 AuthService 和 ProjectService 的核心业务逻辑。
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import RegisterRequest, LoginRequest, ProjectCreate, ProjectUpdate, CharacterCreate


class TestAuthService:
    """认证服务测试。"""

    @pytest.mark.asyncio
    async def test_auth_service_register(self, db_session: AsyncSession):
        """认证服务注册 - 应成功注册并返回 token。"""
        from app.services import AuthService

        service = AuthService(db_session)
        req = RegisterRequest(
            username="serviceuser",
            email="service@example.com",
            password="servicepass123",
            display_name="Service User",
        )
        result = await service.register(req)
        assert result is not None
        assert result.access_token is not None
        assert len(result.access_token) > 0

    @pytest.mark.asyncio
    async def test_auth_service_register_duplicate(self, db_session: AsyncSession, test_user: dict):
        """认证服务注册重复用户 - 应抛出异常。"""
        from app.services import AuthService
        from app.core.exceptions import ValidationException

        service = AuthService(db_session)
        req = RegisterRequest(
            username=test_user["username"],
            email="another@example.com",
            password="pass123456",
        )
        with pytest.raises(ValidationException) as exc_info:
            await service.register(req)
        assert "用户名" in str(exc_info.value.message) or "已" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_auth_service_login(self, db_session: AsyncSession, test_user: dict):
        """认证服务登录 - 应成功登录并返回 token。"""
        from app.services import AuthService

        service = AuthService(db_session)
        req = LoginRequest(
            username=test_user["username"],
            password=test_user["password"],
        )
        result = await service.login(req)
        assert result is not None
        assert result.access_token is not None

    @pytest.mark.asyncio
    async def test_auth_service_login_invalid(self, db_session: AsyncSession, test_user: dict):
        """认证服务登录密码错误 - 应抛出异常。"""
        from app.services import AuthService
        from app.core.exceptions import UnauthorizedException

        service = AuthService(db_session)
        req = LoginRequest(
            username=test_user["username"],
            password="wrongpassword",
        )
        with pytest.raises(UnauthorizedException) as exc_info:
            await service.login(req)
        assert "密码错误" in str(exc_info.value.message) or "错误" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_auth_service_get_user(self, db_session: AsyncSession, test_user: dict):
        """认证服务获取用户 - 应返回用户信息。"""
        from app.services import AuthService

        service = AuthService(db_session)
        user = await service.get_user(test_user["id"])
        assert user is not None
        assert user.username == test_user["username"]
        assert user.email == test_user["email"]

    @pytest.mark.asyncio
    async def test_auth_service_get_user_not_found(self, db_session: AsyncSession):
        """认证服务获取不存在的用户 - 应返回 None。"""
        from app.services import AuthService

        service = AuthService(db_session)
        fake_id = str(uuid.uuid4())
        user = await service.get_user(fake_id)
        assert user is None


class TestProjectService:
    """项目服务测试。"""

    @pytest.mark.asyncio
    async def test_project_service_create(self, db_session: AsyncSession, test_user: dict):
        """项目服务创建 - 应成功创建项目。"""
        from app.services import ProjectService

        service = ProjectService(db_session)
        req = ProjectCreate(
            name="服务测试项目",
            description="通过服务层创建",
            story_input="测试故事",
            genre="sci-fi",
        )
        project = await service.create(req, user_id=test_user["id"])
        assert project is not None
        assert project.name == "服务测试项目"
        assert project.genre == "sci-fi"

    @pytest.mark.asyncio
    async def test_project_service_create_without_user(self, db_session: AsyncSession):
        """项目服务创建（无用户） - 应成功创建。"""
        from app.services import ProjectService

        service = ProjectService(db_session)
        req = ProjectCreate(
            name="匿名项目",
            description="匿名创建",
            story_input="",
            genre="fantasy",
        )
        project = await service.create(req)
        assert project is not None
        assert project.name == "匿名项目"

    @pytest.mark.asyncio
    async def test_project_service_list(self, db_session: AsyncSession, test_user: dict, test_project: dict):
        """项目服务列表 - 应返回用户的项目列表。"""
        from app.services import ProjectService

        service = ProjectService(db_session)
        projects = await service.list(user_id=test_user["id"])
        assert len(projects) >= 1
        assert any(p.name == test_project["name"] for p in projects)

    @pytest.mark.asyncio
    async def test_project_service_get(self, db_session: AsyncSession, test_project: dict):
        """项目服务获取 - 应返回项目详情。"""
        from app.services import ProjectService

        service = ProjectService(db_session)
        project = await service.get(test_project["id"])
        assert project is not None
        assert project.id == uuid.UUID(test_project["id"])

    @pytest.mark.asyncio
    async def test_project_service_get_not_found(self, db_session: AsyncSession):
        """项目服务获取不存在 - 应返回 None。"""
        from app.services import ProjectService

        service = ProjectService(db_session)
        fake_id = str(uuid.uuid4())
        project = await service.get(fake_id)
        assert project is None

    @pytest.mark.asyncio
    async def test_project_service_update(self, db_session: AsyncSession, test_project: dict):
        """项目服务更新 - 应返回更新后的项目。"""
        from app.services import ProjectService

        service = ProjectService(db_session)
        req = ProjectUpdate(name="更新后的名称")
        project = await service.update(test_project["id"], req)
        assert project is not None
        assert project.name == "更新后的名称"

    @pytest.mark.asyncio
    async def test_project_service_delete(self, db_session: AsyncSession, test_project: dict):
        """项目服务删除 - 应返回 True。"""
        from app.services import ProjectService

        service = ProjectService(db_session)
        result = await service.delete(test_project["id"])
        assert result is True
        # 验证删除后无法获取
        project = await service.get(test_project["id"])
        assert project is None

    @pytest.mark.asyncio
    async def test_project_service_add_character(self, db_session: AsyncSession, test_project: dict):
        """项目服务添加角色 - 应返回角色信息。"""
        from app.services import ProjectService

        service = ProjectService(db_session)
        req = CharacterCreate(
            name="测试角色",
            role="主角",
            age="20",
            gender="女",
            personality="聪明",
            appearance="长发",
            background="神秘背景",
        )
        character = await service.add_character(test_project["id"], req)
        assert character is not None
        assert character.name == "测试角色"
        assert character.role == "主角"

    @pytest.mark.asyncio
    async def test_project_service_list_characters(self, db_session: AsyncSession, test_project: dict):
        """项目服务列出角色 - 应返回角色列表。"""
        from app.services import ProjectService

        service = ProjectService(db_session)
        # 先添加角色
        req = CharacterCreate(name="角色A", role="主角")
        await service.add_character(test_project["id"], req)

        req2 = CharacterCreate(name="角色B", role="配角")
        await service.add_character(test_project["id"], req2)

        characters = await service.list_characters(test_project["id"])
        assert len(characters) == 2
        assert any(c.name == "角色A" for c in characters)
        assert any(c.name == "角色B" for c in characters)