from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    PROJECT_NAME: str = "TRACE-X"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "tracex-secret-key-for-sih26151-demo-2026")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Neo4j settings
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "tracex2026")
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*"
    ]
    
    # Default Fusion Weights
    DEFAULT_WEIGHT_CRYPTO: float = 0.30
    DEFAULT_WEIGHT_FINANCIAL: float = 0.25
    DEFAULT_WEIGHT_STYLOMETRY: float = 0.20
    DEFAULT_WEIGHT_INFRASTRUCTURE: float = 0.15
    DEFAULT_WEIGHT_BEHAVIORAL: float = 0.10

    class Config:
        case_sensitive = True


settings = Settings()
