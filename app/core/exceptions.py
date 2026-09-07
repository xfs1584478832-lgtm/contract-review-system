from fastapi import Request
from fastapi.responses import JSONResponse
from app.utils.logger import logger


class BusinessException(Exception):
    """业务异常基类"""
    def __init__(self, code: int = 400, message: str = "业务异常"):
        self.code = code
        self.message = message


class NotFoundException(BusinessException):
    """资源不存在"""
    def __init__(self, message: str = "资源不存在"):
        super().__init__(code=404, message=message)


class UnauthorizedException(BusinessException):
    """未授权"""
    def __init__(self, message: str = "未授权"):
        super().__init__(code=401, message=message)


class ForbiddenException(BusinessException):
    """无权限"""
    def __init__(self, message: str = "无权限"):
        super().__init__(code=403, message=message)


async def business_exception_handler(request: Request, exc: BusinessException):
    """业务异常处理器"""
    logger.warning(f"业务异常: {exc.code} - {exc.message} - {request.url.path}")
    return JSONResponse(
        status_code=200,
        content={"code": exc.code, "message": exc.message, "data": None}
    )


async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    logger.error(f"系统异常: {str(exc)} - {request.url.path}", exc_info=True)
    return JSONResponse(
        status_code=200,
        content={"code": 500, "message": "服务器内部错误", "data": None}
    )

