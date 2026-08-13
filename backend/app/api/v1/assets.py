from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import EpisodeCreate, EpisodeUpdate, SceneCreate, PropCreate, VoiceCreate
from app.utils.response import success_response
from app.services.manage_service import AssetService

router = APIRouter()


# ===== Episodes =====
@router.get("/{project_id}/episodes")
async def list_episodes(project_id: str, db: AsyncSession = Depends(get_db)):
    service = AssetService(db)
    items = await service.get_episodes(project_id)
    return success_response(items)


@router.post("/{project_id}/episodes")
async def create_episode(project_id: str, req: EpisodeCreate, db: AsyncSession = Depends(get_db)):
    service = AssetService(db)
    episode = await service.create_episode(project_id, req)
    return success_response(episode.model_dump(mode='json'))


@router.put("/{project_id}/episodes/{episode_id}")
async def update_episode(project_id: str, episode_id: str, req: EpisodeUpdate, db: AsyncSession = Depends(get_db)):
    service = AssetService(db)
    episode = await service.update_episode(episode_id, req)
    return success_response(episode.model_dump(mode='json'))


# ===== Scenes =====
@router.get("/{project_id}/scenes")
async def list_scenes(project_id: str, db: AsyncSession = Depends(get_db)):
    service = AssetService(db)
    items = await service.get_scenes(project_id)
    return success_response(items)


@router.post("/{project_id}/scenes")
async def create_scene(project_id: str, req: SceneCreate, db: AsyncSession = Depends(get_db)):
    service = AssetService(db)
    scene = await service.create_scene(project_id, req)
    return success_response(scene.model_dump(mode='json'))


# ===== Props =====
@router.get("/{project_id}/props")
async def list_props(project_id: str, db: AsyncSession = Depends(get_db)):
    service = AssetService(db)
    items = await service.get_props(project_id)
    return success_response(items)


@router.post("/{project_id}/props")
async def create_prop(project_id: str, req: PropCreate, db: AsyncSession = Depends(get_db)):
    service = AssetService(db)
    prop = await service.create_prop(project_id, req)
    return success_response(prop.model_dump(mode='json'))


# ===== Voices =====
@router.get("/{project_id}/voices")
async def list_voices(project_id: str, db: AsyncSession = Depends(get_db)):
    service = AssetService(db)
    items = await service.get_voices(project_id)
    return success_response(items)


@router.post("/{project_id}/voices")
async def create_voice(project_id: str, req: VoiceCreate, db: AsyncSession = Depends(get_db)):
    service = AssetService(db)
    voice = await service.create_voice(project_id, req)
    return success_response(voice.model_dump(mode='json'))