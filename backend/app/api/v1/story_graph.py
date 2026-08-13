from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import CharacterRelationshipCreate
from app.utils.response import success_response
from app.services.manage_service import StoryGraphService

router = APIRouter()


@router.get("/{project_id}")
async def list_relationships(project_id: str, db: AsyncSession = Depends(get_db)):
    service = StoryGraphService(db)
    items = await service.get_all(project_id)
    return success_response(items)


@router.post("/{project_id}")
async def create_relationship(project_id: str, req: CharacterRelationshipCreate, db: AsyncSession = Depends(get_db)):
    service = StoryGraphService(db)
    rel = await service.create(project_id, req)
    return success_response(rel.model_dump(mode='json'))


@router.delete("/{project_id}/{rel_id}")
async def delete_relationship(project_id: str, rel_id: str, db: AsyncSession = Depends(get_db)):
    service = StoryGraphService(db)
    ok = await service.delete(rel_id)
    if not ok:
        raise HTTPException(404, "关系不存在")
    return success_response(message="删除成功")