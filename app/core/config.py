import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "RecoverAI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    SIMULATION_MODE: bool = True
    
    # Database URL: default to SQLite for zero-config local run, or PostgreSQL
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./recoverai.db")
    
    # Redis URL
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Security
    JWT_SECRET: str = os.getenv("JWT_SECRET", "super-secret-recoverai-security-key-2026-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # LLM Service API Key
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*",
    ]

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
