from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.utils.response import success_response
from app.services.manage_service import TaskService

router = APIRouter()


@router.get("")
async def list_tasks(project_id: str = None, db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    items = await service.list(project_id)
    return success_response(items)


@router.get("/{task_id}")
async def get_task(task_id: str, db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    task = await service.get(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    return success_response(task.model_dump(mode='json'))


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str, db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    task = await service.cancel(task_id)
    return success_response(task.model_dump(mode='json'))


@router.post("/generate-image")
async def generate_image(req: dict, db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    task = await service.generate_image(
        req.get("project_id", ""), req.get("storyboard_id", ""), req.get("prompt", "")
    )
    return success_response(task.model_dump(mode='json'))


@router.post("/compose-video")
async def compose_video(req: dict, db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    task = await service.compose_video(req.get("project_id", ""), req.get("episode_id", ""))
    return success_response(task.model_dump(mode='json'))


@router.post("/generate-voiceover")
async def generate_voiceover(req: dict, db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    task = await service.generate_voiceover(
        req.get("project_id", ""), req.get("episode_id", ""), req.get("text", "")
    )
    return success_response(task.model_dump(mode='json'))


@router.get("/pending/generation")
async def get_pending_generations(db: AsyncSession = Depends(get_db)):
    """获取所有待处理的图像生成和视频合成任务"""
    service = TaskService(db)
    items = await service.get_pending_generations()
    return success_response(items)


@router.post("/{task_id}/submit-generation")
async def submit_generation(task_id: str, req: dict, db: AsyncSession = Depends(get_db)):
    """提交生成结果（由处理程序调用）"""
    service = TaskService(db)
    task = await service.submit_generation_result(task_id, req.get("result", {}))
    if not task:
        raise HTTPException(404, "任务不存在")
    return success_response(task.model_dump(mode='json'))