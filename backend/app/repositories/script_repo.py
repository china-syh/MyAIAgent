from app.repositories.base import BaseRepository
from app.models.project import Script
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID


class ScriptRepository(BaseRepository[Script]):
    def __init__(self, db):
        super().__init__(Script, db)

    async def get_by_project(self, project_id: UUID) -> List[Script]:
        result = await self.db.execute(
            select(Script).where(Script.project_id == project_id).order_by(Script.chapter_number)
        )
        return result.scalars().all()

    async def get_latest_by_project(self, project_id: UUID) -> Optional[Script]:
        result = await self.db.execute(
            select(Script)
            .where(Script.project_id == project_id)
            .order_by(Script.chapter_number.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()