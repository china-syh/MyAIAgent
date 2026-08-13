from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import ProjectCreate, ProjectUpdate, ProjectResponse, CharacterCreate, CharacterResponse
from app.utils.response import success_response
from app.services import ProjectService
from app.api.deps import get_optional_user
from app.models.user import User
from typing import Optional

router = APIRouter()


@router.get("/", response_model=dict)
async def list_projects(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    service = ProjectService(db)
    user_id = str(current_user.id) if current_user else None
    projects = await service.list(user_id=user_id)
    return success_response([p.model_dump(mode='json') for p in projects])


@router.post("/", response_model=dict)
async def create_project(
    req: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    service = ProjectService(db)
    user_id = str(current_user.id) if current_user else None
    project = await service.create(req, user_id=user_id)
    return success_response(project.model_dump(mode='json'))


@router.get("/{project_id}", response_model=dict)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return success_response(project.model_dump(mode='json'))


@router.put("/{project_id}", response_model=dict)
async def update_project(project_id: str, req: ProjectUpdate, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.update(project_id, req)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return success_response(project.model_dump(mode='json'))


@router.delete("/{project_id}", response_model=dict)
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    ok = await service.delete(project_id)
    if not ok:
        raise HTTPException(status_code=404, detail="项目不存在")
    return success_response(message="删除成功")


@router.get("/{project_id}/characters", response_model=dict)
async def list_characters(project_id: str, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    chars = await service.list_characters(project_id)
    return success_response([c.model_dump(mode='json') for c in chars])


@router.post("/{project_id}/characters", response_model=dict)
async def add_character(project_id: str, req: CharacterCreate, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    # 先检查项目是否存在
    project = await service.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    char = await service.add_character(project_id, req)
    return success_response(char.model_dump(mode='json'))