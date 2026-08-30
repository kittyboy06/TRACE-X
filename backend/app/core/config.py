from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List
import os


class Settings(BaseSettings):
    model_config = ConfigDict(case_sensitive=True)

    PROJECT_NAME: str = "TRACE-X"
    API_V1_STR: str = "/api/v1"
    
    # Development defaults explicitly labeled for SIH sandbox demo
    SECRET_KEY: str = os.getenv("SECRET_KEY", "DEV_SECRET_KEY_FOR_LOCAL_SIH_DEMO_ONLY_NOT_PROD")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Neo4j settings
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "DEV_NEO4J_PASSWORD_SIH26151")
    
    # Model configuration (Transformer enabled by default)
    STYLOMETRY_MODEL: str = os.getenv("STYLOMETRY_MODEL", "all-MiniLM-L6-v2")
    ENABLE_REAL_TRANSFORMER: bool = os.getenv("ENABLE_REAL_TRANSFORMER", "true").lower() in ("true", "1", "yes")
    
    # CORS (specific allowed origins for credentials security)
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://localhost:8000"
    ]
    
    # Default Fusion Weights
    DEFAULT_WEIGHT_CRYPTO: float = 0.30
    DEFAULT_WEIGHT_FINANCIAL: float = 0.25
    DEFAULT_WEIGHT_STYLOMETRY: float = 0.20
    DEFAULT_WEIGHT_INFRASTRUCTURE: float = 0.15
    DEFAULT_WEIGHT_BEHAVIORAL: float = 0.10


settings = Settings()
