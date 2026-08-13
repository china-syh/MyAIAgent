from app.repositories.base import BaseRepository
from app.models.project import Storyboard
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID


class StoryboardRepository(BaseRepository[Storyboard]):
    def __init__(self, db):
        super().__init__(Storyboard, db)

    async def get_by_project(self, project_id: UUID) -> List[Storyboard]:
        result = await self.db.execute(
            select(Storyboard)
            .where(Storyboard.project_id == project_id)
            .order_by(Storyboard.scene_number, Storyboard.panel_number)
        )
        return result.scalars().all()

    async def get_by_script(self, script_id: UUID) -> List[Storyboard]:
        result = await self.db.execute(
            select(Storyboard)
            .where(Storyboard.script_id == script_id)
            .order_by(Storyboard.scene_number, Storyboard.panel_number)
        )
        return result.scalars().all()

    async def bulk_create(self, items: list[dict]) -> List[Storyboard]:
        objs = [self.model(**item) for item in items]
        for obj in objs:
            self.db.add(obj)
        await self.db.commit()
        for obj in objs:
            await self.db.refresh(obj)
        return objs