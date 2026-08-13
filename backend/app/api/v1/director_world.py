from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import DirectorWorldCreate
from app.utils.response import success_response
from app.services.manage_service import DirectorWorldService

router = APIRouter()


@router.get("/{project_id}")
async def list_worlds(project_id: str, db: AsyncSession = Depends(get_db)):
    service = DirectorWorldService(db)
    items = await service.get_all(project_id)
    return success_response(items)


@router.post("/{project_id}")
async def create_world(project_id: str, req: DirectorWorldCreate, db: AsyncSession = Depends(get_db)):
    service = DirectorWorldService(db)
    world = await service.create(project_id, req)
    return success_response(world.model_dump(mode='json'))


@router.delete("/{project_id}/{world_id}")
async def delete_world(project_id: str, world_id: str, db: AsyncSession = Depends(get_db)):
    service = DirectorWorldService(db)
    ok = await service.delete(world_id)
    if not ok:
        raise HTTPException(404, "场景不存在")
    return success_response(message="删除成功")