from typing import Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile as FastAPIUploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.upload_service import (
    UploadService,
    get_image_upload_service,
    get_attachment_upload_service,
)
from app.utils.response import success_response, error_response

router = APIRouter()


@router.post("/image", summary="上传图片")
async def upload_image(
    file: FastAPIUploadFile = File(...),
    sub_dir: Optional[str] = Query("", description="子目录名称，用于分类存储"),
    db: AsyncSession = Depends(get_db),
):
    """上传图片文件，支持格式: jpg, jpeg, png, gif, webp, bmp, svg"""
    service = get_image_upload_service()
    result = await service.save_upload(file, sub_dir=sub_dir or "images")
    return success_response(result.model_dump(), message="图片上传成功")


@router.post("/attachment", summary="上传附件")
async def upload_attachment(
    file: FastAPIUploadFile = File(...),
    sub_dir: Optional[str] = Query("", description="子目录名称，用于分类存储"),
    db: AsyncSession = Depends(get_db),
):
    """上传附件文件，支持格式: 图片 + pdf, doc, docx, xls, xlsx, ppt, pptx, txt, csv, zip, rar, 7z 等"""
    service = get_attachment_upload_service()
    result = await service.save_upload(file, sub_dir=sub_dir or "attachments")
    return success_response(result.model_dump(), message="附件上传成功")


@router.delete("/{file_name}", summary="删除文件")
async def delete_file(
    file_name: str,
    sub_dir: Optional[str] = Query("", description="文件所在子目录"),
    db: AsyncSession = Depends(get_db),
):
    """删除已上传的文件"""
    service = UploadService()
    file_path = f"{sub_dir}/{file_name}" if sub_dir else file_name
    success = service.delete_file(file_path)
    if success:
        return success_response(message="文件删除成功")
    return error_response("DELETE_FAILED", "文件删除失败，文件可能不存在")


@router.get("/{file_name}/info", summary="获取文件信息")
async def get_file_info(
    file_name: str,
    sub_dir: Optional[str] = Query("", description="文件所在子目录"),
    db: AsyncSession = Depends(get_db),
):
    """获取文件的元信息"""
    service = UploadService()
    file_path = f"{sub_dir}/{file_name}" if sub_dir else file_name
    info = service.get_file_info(file_path)
    return success_response(info, message="获取文件信息成功")