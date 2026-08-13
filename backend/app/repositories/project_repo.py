from app.repositories.base import BaseRepository
from app.models.project import Project
from sqlalchemy import select, func
from typing import Optional, List
from uuid import UUID


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, db):
        super().__init__(Project, db)

    async def get_by_user(self, user_id: UUID) -> List[Project]:
        result = await self.db.execute(
            select(Project).where(Project.user_id == user_id).order_by(Project.created_at.desc())
        )
        return result.scalars().all()

    async def get_with_characters(self, project_id: UUID) -> Optional[Project]:
        from sqlalchemy.orm import selectinload
        result = await self.db.execute(
            select(Project)
            .where(Project.id == project_id)
            .options(selectinload(Project.characters))
        )
        return result.scalar_one_or_none()

    async def get_stats(self, user_id: Optional[UUID] = None) -> dict:
        query = select(Project.status, func.count(Project.id))
        if user_id:
            query = query.where(Project.user_id == user_id)
        query = query.group_by(Project.status)
        result = await self.db.execute(query)
        rows = result.all()
        stats = {"draft": 0, "generating": 0, "completed": 0, "failed": 0, "total": 0}
        for status, count in rows:
            stats[status] = count
            stats["total"] += count
        return stats

    async def search_by_name(self, keyword: str, user_id: Optional[UUID] = None) -> List[Project]:
        query = select(Project).where(Project.name.ilike(f"%{keyword}%"))
        if user_id:
            query = query.where(Project.user_id == user_id)
        query = query.order_by(Project.created_at.desc())
        result = await self.db.execute(query)
        return result.scalars().all()