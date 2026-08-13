from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import FreezoneNodeCreate, FreezoneNodeUpdate
from app.utils.response import success_response
from app.services.manage_service import FreezoneService

router = APIRouter()


@router.get("/{project_id}")
async def list_nodes(project_id: str, db: AsyncSession = Depends(get_db)):
    service = FreezoneService(db)
    items = await service.get_all(project_id)
    return success_response(items)


@router.post("/{project_id}")
async def create_node(project_id: str, req: FreezoneNodeCreate, db: AsyncSession = Depends(get_db)):
    service = FreezoneService(db)
    node = await service.create(project_id, req)
    return success_response(node.model_dump(mode='json'))


@router.put("/{project_id}/{node_id}")
async def update_node(project_id: str, node_id: str, req: FreezoneNodeUpdate, db: AsyncSession = Depends(get_db)):
    service = FreezoneService(db)
    node = await service.update(node_id, req)
    if not node:
        raise HTTPException(404, "节点不存在")
    return success_response(node.model_dump(mode='json'))


@router.delete("/{project_id}/{node_id}")
async def delete_node(project_id: str, node_id: str, db: AsyncSession = Depends(get_db)):
    service = FreezoneService(db)
    ok = await service.delete(node_id)
    if not ok:
        raise HTTPException(404, "节点不存在")
    return success_response(message="删除成功")