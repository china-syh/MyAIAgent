from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from typing import Any, Dict, Optional


class AppException(Exception):
    def __init__(self, status_code: int, code: str, message: str, detail: Optional[Any] = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.detail = detail


class NotFoundException(AppException):
    def __init__(self, message: str = "资源不存在", detail: Optional[Any] = None):
        super().__init__(status_code=404, code="NOT_FOUND", message=message, detail=detail)


class ForbiddenException(AppException):
    def __init__(self, message: str = "无权限访问", detail: Optional[Any] = None):
        super().__init__(status_code=403, code="FORBIDDEN", message=message, detail=detail)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "未登录或登录已过期", detail: Optional[Any] = None):
        super().__init__(status_code=401, code="UNAUTHORIZED", message=message, detail=detail)


class ValidationException(AppException):
    def __init__(self, message: str = "参数验证失败", detail: Optional[Any] = None):
        super().__init__(status_code=422, code="VALIDATION_ERROR", message=message, detail=detail)


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "detail": exc.detail,
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "detail": str(exc) if __debug__ else None,
            },
        )