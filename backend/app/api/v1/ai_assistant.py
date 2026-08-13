from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import AIChatCreate
from app.utils.response import success_response
from app.services.manage_service import AIAssistantService

router = APIRouter()


@router.get("/chat/{project_id}")
async def get_chat(project_id: str, db: AsyncSession = Depends(get_db)):
    service = AIAssistantService(db)
    messages = await service.get_chat(project_id)
    return success_response(messages)


@router.post("/chat")
async def send_message(req: AIChatCreate, db: AsyncSession = Depends(get_db)):
    service = AIAssistantService(db)
    result = await service.send_message(req)
    return success_response(result)


@router.post("/chat/{project_id}")
async def send_message_with_project(project_id: str, req: dict, db: AsyncSession = Depends(get_db)):
    service = AIAssistantService(db)
    data = AIChatCreate(
        project_id=project_id,
        content=req.get("content", ""),
        message_type=req.get("message_type", "text"),
        meta_data=req.get("meta_data", {}),
    )
    result = await service.send_message(data)
    return success_response(result)