from app.repositories.base import BaseRepository
from app.models.project import Character
from sqlalchemy import select
from typing import List
from uuid import UUID


class CharacterRepository(BaseRepository[Character]):
    def __init__(self, db):
        super().__init__(Character, db)

    async def get_by_project(self, project_id: UUID) -> List[Character]:
        result = await self.db.execute(
            select(Character).where(Character.project_id == project_id)
        )
        return result.scalars().all()

    async def batch_create(self, items: List[dict]) -> List[Character]:
        objs = [Character(**item) for item in items]
        for obj in objs:
            self.db.add(obj)
        await self.db.commit()
        for obj in objs:
            await self.db.refresh(obj)
        return objs