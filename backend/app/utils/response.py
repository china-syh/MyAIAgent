from typing import Any, Optional
from fastapi.responses import JSONResponse


def success_response(data: Any = None, message: str = "success") -> dict:
    return {"code": 0, "message": message, "data": data}


def error_response(code: str, message: str, detail: Any = None) -> dict:
    return {"code": code, "message": message, "detail": detail}


def api_response(data: Any = None, message: str = "success", code: int = 0) -> JSONResponse:
    return JSONResponse(content={"code": code, "message": message, "data": data})