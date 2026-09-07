from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.api.v1 import api_router
from app.core.exceptions import (
    BusinessException,
    business_exception_handler,
    global_exception_handler
)
from app.utils.logger import logger

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="基于 RAG + 多 Agent + 微调的智能合同审查系统"
)

# 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册异常处理器
app.add_exception_handler(BusinessException, business_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# 注册 API 路由
app.include_router(api_router)


@app.on_event("startup")
async def startup_event():
    """启动时执行"""
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} 启动成功")
    logger.info(f"API 文档地址: http://127.0.0.1:8000/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """关闭时执行"""
    logger.info("应用关闭")


@app.get("/")
async def root():
    """首页"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "api": "/api/v1/health"
    }
