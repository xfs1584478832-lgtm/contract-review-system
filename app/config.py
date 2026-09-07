from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置，从 .env 文件读取"""
    
    # 应用
    APP_NAME: str = "法眼-智能合同审查助手"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # 数据库
    DATABASE_URL: str = "sqlite:///./data/contract_review.db"
    
    # 大模型
    SILICONFLOW_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.siliconflow.cn/v1"
    LLM_MODEL: str = "deepseek-ai/DeepSeek-V3"
    EMBEDDING_MODEL: str = "shibing624/text2vec-base-chinese"
    
    # 安全
    SECRET_KEY: str = "your-secret-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # 向量库
    CHROMA_PATH: str = "./data/chroma_db"
    
    # 文件
    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE: int = 52428800  # 50MB
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
