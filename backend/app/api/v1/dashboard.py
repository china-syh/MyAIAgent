from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import DashboardStats
from app.utils.response import success_response
from app.services import ProjectService

router = APIRouter()


@router.get("/stats", response_model=dict)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    stats = await service.get_stats()
    return success_response(stats.model_dump())