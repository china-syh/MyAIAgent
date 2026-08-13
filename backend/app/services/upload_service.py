import os
import uuid
import logging
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import UploadFile, HTTPException
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)


class UploadResponse(BaseModel):
    """文件上传响应模型"""
    file_name: str
    original_name: str
    file_path: str
    file_url: str
    file_size: int
    mime_type: str
    extension: str
    created_at: str


class UploadService:
    """文件上传服务"""

    # 图片类型白名单
    IMAGE_EXTENSIONS: List[str] = ["jpg", "jpeg", "png", "gif", "webp", "bmp", "svg"]
    # 附件类型白名单
    ATTACHMENT_EXTENSIONS: List[str] = [
        "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
        "txt", "csv", "zip", "rar", "7z",
    ]

    def __init__(self, allowed_extensions: Optional[List[str]] = None, max_size: Optional[int] = None):
        self.allowed_extensions = allowed_extensions or settings.ALLOWED_EXTENSIONS
        self.max_size = max_size or settings.MAX_UPLOAD_SIZE
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.base_url = getattr(settings, "BASE_URL", "http://localhost:8000")

    def _validate_extension(self, filename: str) -> str:
        """校验文件扩展名是否在白名单内"""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if not ext:
            raise HTTPException(status_code=400, detail="文件缺少扩展名")
        if ext not in self.allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型 '.{ext}'，允许的类型: {', '.join(self.allowed_extensions)}",
            )
        return ext

    def _validate_file_size(self, file_size: int) -> None:
        """校验文件大小是否超限"""
        if file_size > self.max_size:
            max_size_mb = self.max_size / (1024 * 1024)
            raise HTTPException(
                status_code=400,
                detail=f"文件大小超过限制 ({max_size_mb:.1f}MB)",
            )

    def _ensure_dir(self, sub_dir: str = "") -> Path:
        """确保目标目录存在，自动创建多级目录结构"""
        target_dir = self.upload_dir
        if sub_dir:
            target_dir = target_dir / sub_dir
        target_dir = target_dir.resolve()
        # 防止目录遍历攻击
        if not str(target_dir).startswith(str(self.upload_dir.resolve())):
            raise HTTPException(status_code=400, detail="非法的子目录路径")
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir

    def _generate_unique_filename(self, original_name: str) -> str:
        """生成唯一文件名，保留原始扩展名"""
        ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
        unique_name = f"{uuid.uuid4().hex}_{int(datetime.now().timestamp())}"
        if ext:
            unique_name = f"{unique_name}.{ext}"
        return unique_name

    def _detect_mime_type(self, filename: str) -> str:
        """根据文件扩展名检测 MIME 类型"""
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or "application/octet-stream"

    async def save_upload(self, file: UploadFile, sub_dir: str = "") -> UploadResponse:
        """保存上传文件，返回文件元信息

        Args:
            file: FastAPI UploadFile 对象
            sub_dir: 子目录名称，用于分类存储（如 images/, attachments/）

        Returns:
            UploadResponse: 包含文件元信息的响应对象
        """
        # 校验文件扩展名
        original_name = file.filename or "unknown"
        ext = self._validate_extension(original_name)

        # 读取文件内容并校验大小
        content = await file.read()
        file_size = len(content)
        self._validate_file_size(file_size)

        # 生成唯一文件名，确保目录存在
        unique_name = self._generate_unique_filename(original_name)
        target_dir = self._ensure_dir(sub_dir)
        file_path = target_dir / unique_name

        # 写入文件
        with open(file_path, "wb") as f:
            f.write(content)

        # 构建相对路径和 URL
        relative_path = str(Path(sub_dir) / unique_name) if sub_dir else unique_name
        file_url = self.get_file_url(relative_path)

        logger.info(
            f"文件上传成功: {original_name} -> {relative_path} "
            f"({file_size / 1024:.1f}KB)"
        )

        return UploadResponse(
            file_name=unique_name,
            original_name=original_name,
            file_path=relative_path,
            file_url=file_url,
            file_size=file_size,
            mime_type=self._detect_mime_type(original_name),
            extension=ext,
            created_at=datetime.now().isoformat(),
        )

    def delete_file(self, file_path: str) -> bool:
        """删除文件

        Args:
            file_path: 文件的相对路径或绝对路径

        Returns:
            bool: 是否删除成功
        """
        # 支持相对路径和绝对路径
        path = Path(file_path)
        if not path.is_absolute():
            path = self.upload_dir / path
        path = path.resolve()

        # 安全检查：确保路径在 upload_dir 内
        if not str(path).startswith(str(self.upload_dir.resolve())):
            logger.warning(f"尝试删除上传目录外的文件: {path}")
            raise HTTPException(status_code=400, detail="不允许删除上传目录外的文件")

        if not path.exists():
            logger.warning(f"文件不存在: {path}")
            return False

        if not path.is_file():
            logger.warning(f"路径不是文件: {path}")
            return False

        try:
            path.unlink()
            logger.info(f"文件已删除: {path}")
            return True
        except OSError as e:
            logger.error(f"删除文件失败: {path}, 错误: {e}")
            return False

    def get_file_url(self, file_path: str) -> str:
        """获取文件访问 URL

        Args:
            file_path: 文件的相对路径

        Returns:
            str: 完整的文件访问 URL
        """
        # 确保路径分隔符为 /
        normalized_path = file_path.replace("\\", "/")
        return f"{self.base_url.rstrip('/')}/uploads/{normalized_path.lstrip('/')}"

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """获取文件元信息

        Args:
            file_path: 文件的相对路径

        Returns:
            dict: 包含文件元信息的字典
        """
        path = Path(file_path)
        if not path.is_absolute():
            path = self.upload_dir / path
        path = path.resolve()

        # 安全检查
        if not str(path).startswith(str(self.upload_dir.resolve())):
            raise HTTPException(status_code=400, detail="不允许访问上传目录外的文件")

        if not path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")

        if not path.is_file():
            raise HTTPException(status_code=400, detail="路径不是文件")

        stat = path.stat()
        relative_path = str(path.relative_to(self.upload_dir))

        return {
            "file_name": path.name,
            "file_path": relative_path,
            "file_url": self.get_file_url(relative_path),
            "file_size": stat.st_size,
            "mime_type": self._detect_mime_type(path.name),
            "extension": path.suffix.lstrip(".").lower(),
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }


# 预配置的图片上传服务实例工厂
def get_image_upload_service() -> UploadService:
    """获取图片上传服务实例（仅允许图片类型）"""
    return UploadService(
        allowed_extensions=UploadService.IMAGE_EXTENSIONS,
        max_size=settings.MAX_UPLOAD_SIZE,
    )


# 预配置的附件上传服务实例工厂
def get_attachment_upload_service() -> UploadService:
    """获取附件上传服务实例（允许图片和文档类型）"""
    allowed = UploadService.IMAGE_EXTENSIONS + UploadService.ATTACHMENT_EXTENSIONS
    return UploadService(
        allowed_extensions=allowed,
        max_size=settings.MAX_UPLOAD_SIZE * 5,  # 附件允许更大文件（50MB）
    )