from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.contract import Contract
from app.services.review_service import review_service
from app.schemas.common import success_response
from app.utils.logger import logger

router = APIRouter(prefix="/review", tags=["合同审查"])


@router.post("/{contract_id}")
async def review_contract(
    contract_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """提交合同智能审查任务（异步执行）

    审查涉及大量 LLM 调用，耗时较长，接口立即返回；
    后台线程执行审查，前端通过 GET /review/{contract_id} 轮询状态。
    """
    try:
        logger.info(f"收到审查请求，合同ID={contract_id}")

        # 检查合同是否存在
        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        if not contract:
            raise HTTPException(status_code=404, detail="合同不存在")

        if not contract.clauses:
            raise HTTPException(status_code=400, detail="合同尚未解析，请先上传解析合同")

        # 防止重复提交
        if contract.status == "reviewing":
            return success_response(
                data={"contract_id": contract_id, "status": "reviewing"},
                message="合同正在审查中，请勿重复提交"
            )

        # 标记审查中并提交（后台任务使用独立会话读取该状态）
        contract.status = "reviewing"
        db.commit()

        # 加入后台任务（同步函数会被 Starlette 放到线程池执行，不阻塞事件循环）
        background_tasks.add_task(review_service.review_contract_background, contract_id)

        return success_response(
            data={"contract_id": contract_id, "status": "reviewing"},
            message="审查任务已提交，请稍后通过 GET /review/{contract_id} 查询结果"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提交审查任务失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{contract_id}")
async def get_review_result(
    contract_id: int,
    db: Session = Depends(get_db)
):
    """查询合同审查结果（也用于轮询审查进度/状态）"""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    # 审查进行中
    if contract.status == "reviewing":
        return success_response(
            data={"contract_id": contract_id, "status": "reviewing"},
            message="合同正在审查中，请稍后再试"
        )

    # 审查失败
    if contract.status == "review_failed":
        error_msg = (contract.review_result or {}).get("error", "未知错误")
        return success_response(
            data={"contract_id": contract_id, "status": "review_failed", "error": error_msg},
            message=f"审查失败：{error_msg}"
        )

    # 尚未审查
    if not contract.review_result:
        raise HTTPException(status_code=400, detail="该合同尚未审查，请先调用审查接口")

    return success_response(data=contract.review_result)
