import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.utils.response import success_response
from app.services.project_service import ProjectService
from app.services.deepseek_service import DeepSeekService, get_system_prompt

logger = logging.getLogger(__name__)
router = APIRouter()
deepseek = DeepSeekService()


@router.post("/parse")
async def parse_novel(data: dict, db: AsyncSession = Depends(get_db)):
    """解析小说文本，提取角色、情节等信息（使用DeepSeek）"""
    project_id = data.get("project_id", "")
    story_input = data.get("story_input", "")
    if not story_input:
        raise HTTPException(400, "请输入小说内容")
    service = ProjectService(db)
    project = await service.get(project_id) if project_id else None
    project_name = project.name if project else "未知作品"

    try:
        result = await deepseek.chat_json(
            messages=[
                {"role": "system", "content": get_system_prompt("novel_parser")},
                {"role": "user", "content": f"作品名称：{project_name}\n\n小说内容：\n{story_input[:8000]}"},
            ],
            temperature=0.3,
        )
        return success_response(result)
    except Exception as e:
        logger.error(f"小说解析失败: {e}")
        raise HTTPException(500, f"解析失败: {str(e)}")


@router.post("/analyze")
async def analyze_story(data: dict, db: AsyncSession = Depends(get_db)):
    """分析故事结构，生成节奏建议（使用DeepSeek）"""
    story_input = data.get("story_input", "")
    if not story_input:
        raise HTTPException(400, "请输入小说内容")

    try:
        result = await deepseek.chat_json(
            messages=[
                {"role": "system", "content": "你是一个故事结构分析专家。分析小说的节奏和张力曲线，以JSON格式返回分析结果，包含：pacing(节奏描述), tension_curve(每章节张力值列表), suggestions(改进建议列表)。"},
                {"role": "user", "content": f"分析以下小说的故事结构：\n\n{story_input[:6000]}"},
            ],
            temperature=0.3,
        )
        return success_response(result)
    except Exception as e:
        logger.error(f"故事分析失败: {e}")
        raise HTTPException(500, f"分析失败: {str(e)}")