from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ContractBase(BaseModel):
    filename: str
    contract_type: Optional[str] = None


class ContractResponse(ContractBase):
    id: int
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    party_a: Optional[str] = None
    party_b: Optional[str] = None
    contract_amount: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    summary: Optional[str] = None
    status: str
    clauses_count: int = 0
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ContractDetailResponse(ContractResponse):
    full_text: Optional[str] = None
    clauses: Optional[List[dict]] = None
    review_result: Optional[dict] = None


class ClauseItem(BaseModel):
    """条款结构"""
    index: int
    title: str
    content: str
    clause_type: Optional[str] = None
