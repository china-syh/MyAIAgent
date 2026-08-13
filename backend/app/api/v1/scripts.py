from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import ScriptResponse, StoryboardResponse
from app.utils.response import success_response
from app.services import ScriptService

router = APIRouter()


@router.get("/{project_id}/scripts", response_model=dict)
async def list_scripts(project_id: str, db: AsyncSession = Depends(get_db)):
    """获取项目的所有剧本"""
    service = ScriptService(db)
    scripts = await service.get_by_project(project_id)
    return success_response([s.model_dump(mode='json') for s in scripts])


@router.get("/{project_id}/scripts/latest", response_model=dict)
async def get_latest_script(project_id: str, db: AsyncSession = Depends(get_db)):
    """获取项目的最新剧本"""
    service = ScriptService(db)
    script = await service.get_latest(project_id)
    if not script:
        return success_response(None, message="暂无剧本")
    return success_response(script.model_dump(mode='json'))


@router.get("/{project_id}/storyboards", response_model=dict)
async def list_storyboards(project_id: str, db: AsyncSession = Depends(get_db)):
    """获取项目的所有分镜"""
    service = ScriptService(db)
    boards = await service.get_storyboards(project_id)
    return success_response([b.model_dump(mode='json') for b in boards])


@router.get("/{project_id}/execute-result", response_model=dict)
async def get_execute_result(project_id: str, db: AsyncSession = Depends(get_db)):
    """获取项目执行结果（剧本+分镜）"""
    service = ScriptService(db)
    result = await service.get_execute_result(project_id)
    if not result:
        return success_response(None, message="项目尚未执行，暂无结果")
    return success_response(result.model_dump(mode='json'))


@router.delete("/{project_id}/scripts/{script_id}", response_model=dict)
async def delete_script(project_id: str, script_id: str, db: AsyncSession = Depends(get_db)):
    """删除指定章节及其所有关联的分镜，并重排章节编号"""
    service = ScriptService(db)
    success = await service.delete_script(project_id, script_id)
    if not success:
        raise HTTPException(404, "章节不存在")
    return success_response(message="章节已删除")
