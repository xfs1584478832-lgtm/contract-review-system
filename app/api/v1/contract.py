import os
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.contract import Contract
from app.schemas.contract import ContractResponse, ContractDetailResponse
from app.services.contract_service import contract_service
from app.schemas.common import success_response
from app.config import settings
from app.utils.logger import logger

router = APIRouter(prefix="/contracts", tags=["合同管理"])


@router.post("/upload")
async def upload_contract(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """上传合同并自动解析"""
    try:
        # 保存文件
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        file_path = os.path.join(settings.UPLOAD_DIR, file.filename)
        
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        file_size = len(content)
        file_type = os.path.splitext(file.filename)[1]
        
        # 解析合同
        parse_result = contract_service.parse_contract(file_path)
        
        # 存入数据库
        db_contract = Contract(
            filename=file.filename,
            contract_type=parse_result["contract_type"],
            file_type=file_type,
            file_size=file_size,
            party_a=parse_result["party_a"],
            party_b=parse_result["party_b"],
            contract_amount=parse_result["contract_amount"],
            contract_amount_num=parse_result["contract_amount_num"],
            start_date=parse_result["start_date"],
            end_date=parse_result["end_date"],
            signing_date=parse_result["signing_date"],
            full_text=parse_result["full_text"],
            clauses=parse_result["clauses"],
            summary=parse_result["summary"],
            status=parse_result["status"],
        )
        db.add(db_contract)
        db.commit()
        db.refresh(db_contract)
        
        logger.info(f"合同上传解析成功: {file.filename}, ID={db_contract.id}")
        
        return success_response(
            data=db_contract.to_dict(),
            message="合同上传并解析成功"
        )
    except Exception as e:
        logger.error(f"合同上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_contracts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    contract_type: str = Query(None),
    db: Session = Depends(get_db)
):
    """获取合同列表"""
    query = db.query(Contract)
    
    if contract_type:
        query = query.filter(Contract.contract_type == contract_type)
    
    total = query.count()
    contracts = query.order_by(Contract.created_at.desc()) \
        .offset((page - 1) * page_size) \
        .limit(page_size) \
        .all()
    
    return {
        "code": 200,
        "message": "success",
        "data": [c.to_dict() for c in contracts],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/{contract_id}")
async def get_contract(
    contract_id: int,
    db: Session = Depends(get_db)
):
    """获取合同详情（含全文和条款）"""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    
    data = contract.to_dict()
    data["full_text"] = contract.full_text
    data["clauses"] = contract.clauses
    data["review_result"] = contract.review_result
    
    return success_response(data=data)


@router.delete("/{contract_id}")
async def delete_contract(
    contract_id: int,
    db: Session = Depends(get_db)
):
    """删除合同"""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    
    db.delete(contract)
    db.commit()
    
    return success_response(message="合同删除成功")
