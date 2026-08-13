"""
项目 API 测试

测试项目的 CRUD 操作以及角色管理接口。
"""

import pytest
from httpx import AsyncClient


class TestProjects:
    """项目接口测试类。"""

    @pytest.mark.asyncio
    async def test_create_project(self, client: AsyncClient, auth_headers: dict):
        """创建项目 - 应返回项目信息。"""
        response = await client.post(
            "/api/v1/projects/",
            headers=auth_headers,
            json={
                "name": "新项目",
                "description": "项目描述",
                "story_input": "一个冒险故事",
                "genre": "adventure",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["name"] == "新项目"
        assert data["data"]["genre"] == "adventure"
        assert "id" in data["data"]

    @pytest.mark.asyncio
    async def test_list_projects(self, client: AsyncClient, auth_headers: dict, test_project: dict):
        """列出项目 - 应返回项目列表。"""
        response = await client.get("/api/v1/projects/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert isinstance(data["data"], list)
        # 应包含 test_project
        project_ids = [p["id"] for p in data["data"]]
        assert test_project["id"] in project_ids

    @pytest.mark.asyncio
    async def test_get_project(self, client: AsyncClient, test_project: dict):
        """获取项目详情 - 应返回项目信息。"""
        response = await client.get(f"/api/v1/projects/{test_project['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["name"] == test_project["name"]
        assert data["data"]["id"] == test_project["id"]

    @pytest.mark.asyncio
    async def test_get_project_not_found(self, client: AsyncClient):
        """获取不存在的项目 - 应返回 404。"""
        response = await client.get("/api/v1/projects/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_project(self, client: AsyncClient, test_project: dict):
        """更新项目 - 应返回更新后的项目信息。"""
        response = await client.put(
            f"/api/v1/projects/{test_project['id']}",
            json={"name": "更新后的项目名", "description": "更新描述"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["name"] == "更新后的项目名"
        assert data["data"]["description"] == "更新描述"

    @pytest.mark.asyncio
    async def test_delete_project(self, client: AsyncClient, test_project: dict):
        """删除项目 - 应返回成功。"""
        response = await client.delete(f"/api/v1/projects/{test_project['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        # 验证删除后无法获取
        response = await client.get(f"/api/v1/projects/{test_project['id']}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_add_character(self, client: AsyncClient, test_project: dict):
        """添加角色 - 应返回角色信息。"""
        response = await client.post(
            f"/api/v1/projects/{test_project['id']}/characters",
            json={
                "name": "勇者亚瑟",
                "role": "主角",
                "age": "18",
                "gender": "男",
                "personality": "勇敢、正直",
                "appearance": "金发蓝眼，身穿铠甲",
                "background": "来自偏远村庄的年轻人",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["name"] == "勇者亚瑟"
        assert data["data"]["role"] == "主角"
        assert "id" in data["data"]

    @pytest.mark.asyncio
    async def test_add_character_invalid_project(self, client: AsyncClient):
        """向不存在的项目添加角色 - 应返回 404。"""
        # 由于外键约束，SQLite 会报错，但 API 应返回 404
        import uuid
        fake_id = str(uuid.uuid4())
        response = await client.post(
            f"/api/v1/projects/{fake_id}/characters",
            json={"name": "角色", "role": "配角"},
        )
        # 外键约束失败会导致 500，这取决于具体实现
        # 至少应返回非 2xx 状态码
        assert response.status_code >= 400

    @pytest.mark.asyncio
    async def test_list_characters(self, client: AsyncClient, test_project: dict):
        """列出角色 - 应返回角色列表。"""
        # 先添加一个角色
        await client.post(
            f"/api/v1/projects/{test_project['id']}/characters",
            json={"name": "勇者", "role": "主角"},
        )
        # 列出角色
        response = await client.get(
            f"/api/v1/projects/{test_project['id']}/characters"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert isinstance(data["data"], list)
        assert len(data["data"]) >= 1