"""
认证 API 测试

测试注册、登录、获取当前用户等认证接口。
"""

import pytest
from httpx import AsyncClient


class TestAuth:
    """认证接口测试类。"""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient, db_session):
        """注册成功 - 应返回 access_token。"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "newpass123",
                "display_name": "New User",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["message"] == "success"
        assert "access_token" in data["data"]

    @pytest.mark.asyncio
    async def test_register_duplicate(self, client: AsyncClient, test_user: dict):
        """重复注册失败 - 应返回验证错误。"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": test_user["username"],
                "email": "another@example.com",
                "password": "newpass123",
            },
        )
        # 重复用户名应返回 422
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user: dict):
        """登录成功 - 应返回 access_token。"""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "access_token" in data["data"]

    @pytest.mark.asyncio
    async def test_login_invalid_password(self, client: AsyncClient, test_user: dict):
        """密码错误 - 应返回 401。"""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user["username"],
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401
        data = response.json()
        assert data["code"] == "UNAUTHORIZED"

    @pytest.mark.asyncio
    async def test_get_me(self, client: AsyncClient, auth_headers: dict):
        """获取当前用户 - 应返回用户信息。"""
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_get_me_unauthorized(self, client: AsyncClient):
        """未授权访问 /me - 应返回 401 或 403（中间件拒绝）。"""
        response = await client.get("/api/v1/auth/me")
        # 由于 TrustedHostMiddleware 在测试环境中可能返回 403
        assert response.status_code in (401, 403)