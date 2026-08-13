from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import StyleTemplateCreate
from app.utils.response import success_response
from app.services.manage_service import StyleTemplateService

router = APIRouter()


@router.get("")
async def list_templates(project_id: str = None, db: AsyncSession = Depends(get_db)):
    service = StyleTemplateService(db)
    items = await service.get_all(project_id)
    return success_response(items)


@router.post("")
async def create_template(req: StyleTemplateCreate, db: AsyncSession = Depends(get_db)):
    service = StyleTemplateService(db)
    template = await service.create(req.project_id or "", req)
    return success_response(template.model_dump(mode='json'))


@router.post("/{template_id}/apply")
async def apply_template(template_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """将风格模板应用到项目"""
    project_id = data.get("project_id", "")
    # 模拟应用结果
    result = {
        "template_id": template_id,
        "project_id": project_id,
        "applied": True,
        "scenes_updated": 0,
    }
    return success_response(result)


@router.delete("/{template_id}")
async def delete_template(template_id: str, db: AsyncSession = Depends(get_db)):
    service = StyleTemplateService(db)
    ok = await service.delete(template_id)
    if not ok:
        raise HTTPException(404, "模板不存在")
    return success_response(message="删除成功")