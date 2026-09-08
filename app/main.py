from contextlib import asynccontextmanager
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动和关闭逻辑集中在此"""
    # ===== 启动阶段 =====
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} 启动中...")

    # 创建数据库表
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表初始化完成")

    # 自动导入知识库文档
    try:
        from app.services.knowledge_service import knowledge_service
        import_result = knowledge_service.auto_import()
        logger.info(f"知识库自动导入完成：新增 {import_result['new_imported']} 个文档，共 {import_result['knowledge_base_chunks']} 块")
    except Exception as e:
        logger.warning(f"知识库自动导入失败（不影响服务启动）: {str(e)}")

    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} 启动成功")
    logger.info(f"API 文档地址: http://127.0.0.1:8000/docs")

    yield  # 应用运行中

    # ===== 关闭阶段 =====
    logger.info("应用关闭")

# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="基于 RAG + 多 Agent + 微调的智能合同审查系统",
    lifespan=lifespan,
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


@app.get("/")
async def root():
    """首页"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "api": "/api/v1/health"
    }
