from app.repositories import ScriptRepository, StoryboardRepository, ProjectRepository
from app.models.project import Script, Storyboard, Project
from app.schemas import ScriptResponse, StoryboardResponse, ExecuteResultResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID


class ScriptService:
    def __init__(self, db: AsyncSession):
        self.script_repo = ScriptRepository(db)
        self.storyboard_repo = StoryboardRepository(db)
        self.project_repo = ProjectRepository(db)

    async def get_by_project(self, project_id: str) -> List[ScriptResponse]:
        scripts = await self.script_repo.get_by_project(UUID(project_id))
        return [ScriptResponse.model_validate(s) for s in scripts]

    async def get_storyboards(self, project_id: str) -> List[StoryboardResponse]:
        boards = await self.storyboard_repo.get_by_project(UUID(project_id))
        return [StoryboardResponse.model_validate(b) for b in boards]

    async def get_latest(self, project_id: str) -> Optional[ScriptResponse]:
        script = await self.script_repo.get_latest_by_project(UUID(project_id))
        if not script:
            return None
        return ScriptResponse.model_validate(script)

    async def save_script(self, project_id: str, chapter_number: int, title: str,
                          content: str, scenes: list) -> ScriptResponse:
        script = await self.script_repo.create(
            project_id=UUID(project_id),
            chapter_number=chapter_number,
            title=title,
            content=content,
            scenes=scenes,
            status="completed",
        )
        return ScriptResponse.model_validate(script)

    async def save_storyboards(self, project_id: str, script_id: str,
                               storyboard_data: list[dict]) -> List[StoryboardResponse]:
        items = []
        for item in storyboard_data:
            items.append({
                "project_id": UUID(project_id),
                "script_id": UUID(script_id),
                "scene_number": item.get("scene_number", 1),
                "panel_number": item.get("panel_number", 1),
                "description": item.get("description", ""),
                "composition": item.get("composition", ""),
                "dialogue": item.get("dialogue", ""),
                "camera_angle": item.get("camera_angle", ""),
                "prompt": item.get("prompt", item.get("positive_prompt", "")),
                "status": "completed",
            })
        boards = await self.storyboard_repo.bulk_create(items)
        return [StoryboardResponse.model_validate(b) for b in boards]

    async def get_execute_result(self, project_id: str) -> Optional[ExecuteResultResponse]:
        scripts = await self.script_repo.get_by_project(UUID(project_id))
        if not scripts:
            return None
        storyboards = await self.storyboard_repo.get_by_project(UUID(project_id))
        return ExecuteResultResponse(
            project_id=UUID(project_id),
            scripts=[ScriptResponse.model_validate(s) for s in scripts],
            storyboards=[StoryboardResponse.model_validate(b) for b in storyboards],
        )

    async def delete_script(self, project_id: str, script_id: str) -> bool:
        """删除指定章节及其所有关联的分镜，并重排剩余章节编号"""
        # 1. 删除该章节关联的所有分镜
        storyboards = await self.storyboard_repo.get_by_script(UUID(script_id))
        for sb in storyboards:
            await self.storyboard_repo.delete(sb.id)

        # 2. 删除章节本身
        deleted = await self.script_repo.delete(UUID(script_id))
        if not deleted:
            return False

        # 3. 重排剩余章节编号（保持连续 1, 2, 3...）
        remaining = await self.script_repo.get_by_project(UUID(project_id))
        for idx, script in enumerate(remaining, start=1):
            if script.chapter_number != idx:
                await self.script_repo.update(script.id, chapter_number=idx)

        return True
