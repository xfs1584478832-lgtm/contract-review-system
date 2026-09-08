import os
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from app.services.knowledge_service import knowledge_service
from app.schemas.common import success_response
from app.config import settings
from app.utils.logger import logger

router = APIRouter(prefix="/knowledge", tags=["知识库管理"])


@router.post("/upload")
async def upload_knowledge(file: UploadFile = File(...)):
    """上传法律文档到知识库"""
    try:
        file_path = os.path.join(settings.UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        result = knowledge_service.add_documents(file_path)
        return success_response(data=result, message="文档上传成功")
    except Exception as e:
        logger.error(f"上传文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_knowledge(
    query: str = Query(..., description="检索关键词"),
    top_k: int = Query(3, description="返回结果数量")
):
    """检索知识库"""
    try:
        results = knowledge_service.search(query, top_k=top_k)
        return success_response(data=results, message=f"找到 {len(results)} 条相关内容")
    except Exception as e:
        logger.error(f"检索失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_knowledge_stats():
    """获取知识库统计"""
    stats = knowledge_service.get_stats()
    return success_response(data=stats)


@router.delete("/clear")
async def clear_knowledge():
    """清空知识库"""
    knowledge_service.clear_collection()
    return success_response(message="知识库已清空")


@router.post("/auto-import")
async def auto_import_knowledge():
    """手动触发自动扫描导入（扫描 data/knowledge_base 目录）"""
    try:
        result = knowledge_service.auto_import()
        return success_response(data=result, message="自动导入完成")
    except Exception as e:
        logger.error(f"自动导入失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
