from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.contract import router as contract_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health_router, tags=["健康检查"])
api_router.include_router(knowledge_router)
api_router.include_router(contract_router)
