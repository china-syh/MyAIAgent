from app.repositories import ProjectRepository, CharacterRepository
from app.models.project import Project
from app.schemas import ProjectCreate, ProjectUpdate, ProjectResponse, CharacterCreate, CharacterResponse, DashboardStats
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.repo = ProjectRepository(db)
        self.char_repo = CharacterRepository(db)

    async def create(self, req: ProjectCreate, user_id: Optional[str] = None) -> ProjectResponse:
        kwargs = req.model_dump()
        if user_id:
            kwargs["user_id"] = UUID(user_id)
        project = await self.repo.create(**kwargs)
        return ProjectResponse.model_validate(project)

    async def list(self, user_id: Optional[str] = None) -> List[ProjectResponse]:
        if user_id:
            projects = await self.repo.get_by_user(UUID(user_id))
        else:
            projects = await self.repo.get_multi()
        return [ProjectResponse.model_validate(p) for p in projects]

    async def get(self, project_id: str) -> Optional[ProjectResponse]:
        project = await self.repo.get(UUID(project_id))
        if not project:
            return None
        return ProjectResponse.model_validate(project)

    async def update(self, project_id: str, req: ProjectUpdate) -> Optional[ProjectResponse]:
        kwargs = {k: v for k, v in req.model_dump().items() if v is not None}
        if not kwargs:
            return await self.get(project_id)
        project = await self.repo.update(UUID(project_id), **kwargs)
        if not project:
            return None
        return ProjectResponse.model_validate(project)

    async def delete(self, project_id: str) -> bool:
        return await self.repo.delete(UUID(project_id))

    async def get_stats(self) -> DashboardStats:
        stats = await self.repo.get_stats()
        return DashboardStats(**stats)

    async def add_character(self, project_id: str, req: CharacterCreate) -> CharacterResponse:
        char = await self.char_repo.create(project_id=UUID(project_id), **req.model_dump())
        return CharacterResponse.model_validate(char)

    async def list_characters(self, project_id: str) -> List[CharacterResponse]:
        chars = await self.char_repo.get_by_project(UUID(project_id))
        return [CharacterResponse.model_validate(c) for c in chars]