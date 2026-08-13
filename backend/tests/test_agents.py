"""
Agent 测试

测试规划 Agent、编剧 Agent 的工作流结构。
使用 unittest.mock 模拟 LLM 调用，避免依赖真实 API。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from typing import Dict, Any


class TestPlanningAgent:
    """规划 Agent 测试。"""

    @pytest.mark.asyncio
    @patch("app.agents.planner.ChatOpenAI")
    async def test_planning_agent(self, mock_chat_openai):
        """规划 Agent - 模拟 LLM 返回应解析为结构化结果。"""
        from app.agents.planner import PlanningAgent

        # 模拟 LLM 响应
        mock_llm_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = """```json
{
    "world_setting": {
        "era": "中世纪",
        "location": "幻想大陆"
    },
    "central_conflict": "光明与黑暗的战争",
    "theme": "勇气与友情",
    "target_audience": "青少年",
    "style_reference": "少年漫画风格",
    "characters": [
        {"name": "亚瑟", "role": "主角", "personality": "勇敢", "appearance": "金发", "background": "平民"}
    ]
}
```"""
        mock_llm_instance.invoke.return_value = mock_response
        mock_chat_openai.return_value = mock_llm_instance

        agent = PlanningAgent()
        state: Dict[str, Any] = {
            "story_input": "一个关于勇者斗恶龙的故事",
            "genre": "fantasy",
            "error_count": 0,
        }
        result = agent.run(state)

        assert result["status"] == "planning_completed"
        assert result["world_setting"]["era"] == "中世纪"
        assert result["central_conflict"] == "光明与黑暗的战争"
        assert len(result["characters"]) == 1
        assert result["characters"][0]["name"] == "亚瑟"
        assert "needs_human_approval" in result

    @pytest.mark.asyncio
    @patch("app.agents.planner.ChatOpenAI")
    async def test_planning_agent_failure(self, mock_chat_openai):
        """规划 Agent 失败 - 应返回错误信息。"""
        from app.agents.planner import PlanningAgent

        mock_llm_instance = MagicMock()
        mock_llm_instance.invoke.side_effect = Exception("API 调用失败")
        mock_chat_openai.return_value = mock_llm_instance

        agent = PlanningAgent()
        state: Dict[str, Any] = {
            "story_input": "测试故事",
            "genre": "fantasy",
            "error_count": 0,
        }
        result = agent.run(state)

        assert result["status"] == "failed"
        assert "error" in result
        assert "API 调用失败" in result["error"]
        assert result["error_count"] == 1

    @pytest.mark.asyncio
    @patch("app.agents.planner.ChatOpenAI")
    async def test_planning_agent_parse_raw_json(self, mock_chat_openai):
        """规划 Agent - 解析纯 JSON 响应（无 markdown 代码块）。"""
        from app.agents.planner import PlanningAgent

        mock_llm_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = '{"world_setting": {"era": "未来"}, "central_conflict": "AI vs Human", "characters": []}'
        mock_llm_instance.invoke.return_value = mock_response
        mock_chat_openai.return_value = mock_llm_instance

        agent = PlanningAgent()
        state: Dict[str, Any] = {
            "story_input": "未来故事",
            "genre": "sci-fi",
            "error_count": 0,
        }
        result = agent.run(state)

        assert result["status"] == "planning_completed"
        assert result["world_setting"]["era"] == "未来"
        assert result["central_conflict"] == "AI vs Human"


class TestWritingAgent:
    """编剧 Agent 测试。"""

    @pytest.mark.asyncio
    @patch("app.agents.writer.ChatOpenAI")
    async def test_writing_agent(self, mock_chat_openai):
        """编剧 Agent - 模拟 LLM 返回应解析为剧本结构。"""
        from app.agents.writer import WritingAgent

        mock_llm_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = """```json
{
    "chapter_number": 1,
    "title": "勇者的诞生",
    "outline": ["起: 平静的村庄", "承: 恶龙来袭", "转: 勇者出发", "合: 踏上征途"],
    "scenes": [
        {
            "scene_number": 1,
            "location": "村庄",
            "time": "白天",
            "summary": "日常生活的描写",
            "characters_involved": ["亚瑟"],
            "key_dialogue": "我要成为勇者！"
        }
    ],
    "content": "在遥远的幻想大陆上..."
}```"""
        mock_llm_instance.invoke.return_value = mock_response
        mock_chat_openai.return_value = mock_llm_instance

        agent = WritingAgent()
        state: Dict[str, Any] = {
            "story_input": "勇者故事",
            "world_setting": {"era": "中世纪"},
            "characters": [{"name": "亚瑟", "role": "主角"}],
            "central_conflict": "光明与黑暗",
            "theme": "勇气",
            "error_count": 0,
        }
        result = agent.run(state)

        assert result["status"] == "writing_completed"
        assert result["script"]["chapter_number"] == 1
        assert result["script"]["title"] == "勇者的诞生"
        assert len(result["script"]["scenes"]) == 1
        assert result["chapters"][0]["title"] == "勇者的诞生"

    @pytest.mark.asyncio
    @patch("app.agents.writer.ChatOpenAI")
    async def test_writing_agent_failure(self, mock_chat_openai):
        """编剧 Agent 失败 - 应返回错误信息。"""
        from app.agents.writer import WritingAgent

        mock_llm_instance = MagicMock()
        mock_llm_instance.invoke.side_effect = Exception("LLM 超时")
        mock_chat_openai.return_value = mock_llm_instance

        agent = WritingAgent()
        state: Dict[str, Any] = {
            "story_input": "测试",
            "world_setting": {},
            "characters": [],
            "central_conflict": "",
            "theme": "",
            "error_count": 0,
        }
        result = agent.run(state)

        assert result["status"] == "failed"
        assert "error" in result
        assert "LLM 超时" in result["error"]


class TestWorkflow:
    """工作流结构测试。"""

    def test_workflow_structure(self):
        """工作流 - 应包含所有 Agent 节点和正确的边。"""
        from app.agents.workflow import create_manga_workflow

        graph = create_manga_workflow()

        # 验证图结构
        assert graph is not None

        # 验证节点
        nodes = graph.get_graph().nodes
        node_names = [n for n in nodes.keys()]
        assert "planner" in node_names
        assert "writer" in node_names
        assert "storyboarder" in node_names
        assert "prompter" in node_names
        assert "quality_checker" in node_names

    def test_workflow_routing_functions(self):
        """工作流路由函数 - 应正确返回路由目标。"""
        from app.agents.workflow import route_after_planning, route_after_quality

        # 测试 route_after_planning
        assert route_after_planning({"error": "failed"}) == "failed"
        assert route_after_planning({"status": "completed"}) == "writer"

        # 测试 route_after_quality
        assert route_after_quality({"error": "error"}) == "failed"
        assert route_after_quality({"passed_quality": True}) == "passed"
        assert route_after_quality({"passed_quality": False, "revision_notes": ["note1"]}) == "needs_revision"

    def test_workflow_max_revisions(self):
        """工作流最大修订次数 - 超过限制应强制通过。"""
        from app.agents.workflow import route_after_quality

        # 超过 3 次修订应强制通过
        result = route_after_quality({
            "passed_quality": False,
            "revision_notes": ["n1", "n2", "n3"],
        })
        assert result == "passed"

        # 正好 3 次修订也应强制通过
        result = route_after_quality({
            "passed_quality": False,
            "revision_notes": ["n1", "n2", "n3", "n4"],
        })
        assert result == "passed"

    def test_manga_state_structure(self):
        """MangaState 类型定义 - 应包含所有必要字段。"""
        from app.agents.workflow import MangaState

        # 验证 TypedDict 字段
        required_fields = [
            "project_id", "project_name", "genre", "story_input",
            "world_setting", "central_conflict", "theme",
            "characters", "script", "storyboards", "prompts",
            "quality_report", "passed_quality", "status",
        ]
        for field in required_fields:
            assert field in MangaState.__annotations__, f"缺少字段: {field}"