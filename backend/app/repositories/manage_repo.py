from app.repositories.base import BaseRepository
from app.models.manage import (
    Task, Episode, Scene, Prop, Voice,
    CharacterRelationship, FreezoneNode, DirectorWorld, AIChat, StyleTemplate,
    ProductionRun, ProductionStage,
)
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID


class TaskRepository(BaseRepository[Task]):
    def __init__(self, db):
        super().__init__(Task, db)

    async def get_by_project(self, project_id: UUID) -> List[Task]:
        result = await self.db.execute(
            select(Task).where(Task.project_id == project_id).order_by(Task.created_at.desc())
        )
        return result.scalars().all()

    async def get_by_status(self, status: str) -> List[Task]:
        result = await self.db.execute(
            select(Task).where(Task.status == status).order_by(Task.created_at.desc())
        )
        return result.scalars().all()


class ProductionRunRepository(BaseRepository[ProductionRun]):
    def __init__(self, db):
        super().__init__(ProductionRun, db)

    async def get_latest_by_project(self, project_id: UUID) -> Optional[ProductionRun]:
        result = await self.db.execute(
            select(ProductionRun)
            .where(ProductionRun.project_id == project_id)
            .order_by(ProductionRun.created_at.desc())
        )
        return result.scalars().first()


class ProductionStageRepository(BaseRepository[ProductionStage]):
    def __init__(self, db):
        super().__init__(ProductionStage, db)

    async def get_by_run(self, run_id: UUID) -> List[ProductionStage]:
        result = await self.db.execute(
            select(ProductionStage)
            .where(ProductionStage.run_id == run_id)
            .order_by(ProductionStage.order)
        )
        return result.scalars().all()


class EpisodeRepository(BaseRepository[Episode]):
    def __init__(self, db):
        super().__init__(Episode, db)

    async def get_by_project(self, project_id: UUID) -> List[Episode]:
        result = await self.db.execute(
            select(Episode).where(Episode.project_id == project_id).order_by(Episode.episode_number)
        )
        return result.scalars().all()


class SceneRepository(BaseRepository[Scene]):
    def __init__(self, db):
        super().__init__(Scene, db)

    async def get_by_project(self, project_id: UUID) -> List[Scene]:
        result = await self.db.execute(
            select(Scene).where(Scene.project_id == project_id).order_by(Scene.created_at)
        )
        return result.scalars().all()


class PropRepository(BaseRepository[Prop]):
    def __init__(self, db):
        super().__init__(Prop, db)

    async def get_by_project(self, project_id: UUID) -> List[Prop]:
        result = await self.db.execute(
            select(Prop).where(Prop.project_id == project_id).order_by(Prop.category, Prop.name)
        )
        return result.scalars().all()


class VoiceRepository(BaseRepository[Voice]):
    def __init__(self, db):
        super().__init__(Voice, db)

    async def get_by_project(self, project_id: UUID) -> List[Voice]:
        result = await self.db.execute(
            select(Voice).where(Voice.project_id == project_id).order_by(Voice.character_name)
        )
        return result.scalars().all()


# ===== 故事图谱 =====
class CharacterRelationshipRepository(BaseRepository[CharacterRelationship]):
    def __init__(self, db):
        super().__init__(CharacterRelationship, db)

    async def get_by_project(self, project_id: UUID) -> List[CharacterRelationship]:
        result = await self.db.execute(
            select(CharacterRelationship).where(CharacterRelationship.project_id == project_id)
        )
        return result.scalars().all()

    async def get_by_character(self, character_id: UUID) -> List[CharacterRelationship]:
        result = await self.db.execute(
            select(CharacterRelationship).where(
                (CharacterRelationship.character_a_id == character_id) |
                (CharacterRelationship.character_b_id == character_id)
            )
        )
        return result.scalars().all()


# ===== 自由画布 =====
class FreezoneNodeRepository(BaseRepository[FreezoneNode]):
    def __init__(self, db):
        super().__init__(FreezoneNode, db)

    async def get_by_project(self, project_id: UUID) -> List[FreezoneNode]:
        result = await self.db.execute(
            select(FreezoneNode).where(FreezoneNode.project_id == project_id).order_by(FreezoneNode.order)
        )
        return result.scalars().all()

    async def get_by_type(self, type: str) -> List[FreezoneNode]:
        result = await self.db.execute(
            select(FreezoneNode).where(FreezoneNode.type == type).order_by(FreezoneNode.created_at)
        )
        return result.scalars().all()


# ===== 导演世界 =====
class DirectorWorldRepository(BaseRepository[DirectorWorld]):
    def __init__(self, db):
        super().__init__(DirectorWorld, db)

    async def get_by_project(self, project_id: UUID) -> List[DirectorWorld]:
        result = await self.db.execute(
            select(DirectorWorld).where(DirectorWorld.project_id == project_id).order_by(DirectorWorld.created_at)
        )
        return result.scalars().all()


# ===== AI助手 =====
class AIChatRepository(BaseRepository[AIChat]):
    def __init__(self, db):
        super().__init__(AIChat, db)

    async def get_by_project(self, project_id: UUID) -> List[AIChat]:
        result = await self.db.execute(
            select(AIChat).where(AIChat.project_id == project_id).order_by(AIChat.created_at)
        )
        return result.scalars().all()

    async def get_recent(self, project_id: UUID, limit: int = 50) -> List[AIChat]:
        result = await self.db.execute(
            select(AIChat).where(AIChat.project_id == project_id).order_by(AIChat.created_at.desc()).limit(limit)
        )
        return result.scalars().all()


# ===== 风格模板 =====
class StyleTemplateRepository(BaseRepository[StyleTemplate]):
    def __init__(self, db):
        super().__init__(StyleTemplate, db)

    async def get_by_project(self, project_id: UUID) -> List[StyleTemplate]:
        result = await self.db.execute(
            select(StyleTemplate).where(
                (StyleTemplate.project_id == project_id) | (StyleTemplate.is_global == True)
            ).order_by(StyleTemplate.created_at)
        )
        return result.scalars().all()

    async def get_global(self) -> List[StyleTemplate]:
        result = await self.db.execute(
            select(StyleTemplate).where(StyleTemplate.is_global == True).order_by(StyleTemplate.created_at)
        )
        return result.scalars().all()
