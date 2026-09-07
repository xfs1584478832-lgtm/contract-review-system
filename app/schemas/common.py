from pydantic import BaseModel
from typing import Any, Optional, Generic, TypeVar

T = TypeVar("T")


class ResponseModel(BaseModel, Generic[T]):
    """统一响应格式"""
    code: int = 200
    message: str = "success"
    data: Optional[T] = None


class PageResponseModel(BaseModel, Generic[T]):
    """分页响应格式"""
    code: int = 200
    message: str = "success"
    data: Optional[T] = None
    total: int = 0
    page: int = 1
    page_size: int = 20


def success_response(data: Any = None, message: str = "success") -> dict:
    """成功响应"""
    return {"code": 200, "message": message, "data": data}


def error_response(code: int = 400, message: str = "error") -> dict:
    """错误响应"""
    return {"code": code, "message": message, "data": None}
