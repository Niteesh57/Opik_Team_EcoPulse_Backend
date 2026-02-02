"""
Application configuration settings
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "OPIK Backend API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Security
    SECRET_KEY: str = "YOUR-SECRET-KEY-CHANGE-THIS-IN-PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database
    DATABASE_URL: str = "postgresql://neondb_owner:npg_yFP0mE9xcitg@ep-damp-band-ah1lndo4-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require"
    
    # CORS
    BACKEND_CORS_ORIGINS: list = ["*"]
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    GROQ_API_KEY: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None
    DEAPI_TOKEN: Optional[str] = None
    IMGBB_API_KEY: Optional[str] = None
    XPOZ_API_KEY: Optional[str] = None

    OPIK_URL_OVERRIDE: Optional[str] = None
    OPIK_WORKSPACE: Optional[str] = None
    OPIK_API_KEY: Optional[str] = None
    OPIK_PROJECT_NAME: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
