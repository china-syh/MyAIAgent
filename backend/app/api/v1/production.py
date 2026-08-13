from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import ProductionRunCreate
from app.services.production_service import ProductionService
from app.utils.response import success_response

router = APIRouter()

@router.post("/{project_id}/runs")
async def start_run(project_id: str, req: ProductionRunCreate, db: AsyncSession = Depends(get_db)):
    run = await ProductionService(db).start(project_id, req.story_input, req.genre, req.stages)
    if not run:
        raise HTTPException(404, "project not found")
    return success_response(run)

@router.get("/runs/{run_id}")
async def get_run(run_id: str, db: AsyncSession = Depends(get_db)):
    run = await ProductionService(db).get(run_id)
    if not run:
        raise HTTPException(404, "production run not found")
    return success_response(run)

@router.post("/runs/{run_id}/pause")
async def pause_run(run_id: str, db: AsyncSession = Depends(get_db)):
    run = await ProductionService(db).pause(run_id)
    if not run:
        raise HTTPException(404, "production run not found")
    return success_response(run)

@router.post("/runs/{run_id}/resume")
async def resume_run(run_id: str, db: AsyncSession = Depends(get_db)):
    run = await ProductionService(db).resume(run_id)
    if not run:
        raise HTTPException(404, "production run not found")
    return success_response(run)

@router.post("/runs/{run_id}/stages/{stage_name}/retry")
async def retry_stage(run_id: str, stage_name: str, db: AsyncSession = Depends(get_db)):
    run = await ProductionService(db).retry_stage(run_id, stage_name)
    if not run:
        raise HTTPException(404, "production stage not found")
    return success_response(run)
