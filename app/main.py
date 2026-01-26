"""FastAPI application entry point with automatic database setup and docs paths."""
from contextlib import asynccontextmanager
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.database import init_db

# Detect serverless environment (Vercel uses read-only filesystem)
IS_SERVERLESS = os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")

# Configure structured logging; skip file handler on serverless (read-only FS)
log_handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

if not IS_SERVERLESS:
    os.makedirs("logs", exist_ok=True)
    log_handlers.append(
        RotatingFileHandler("logs/app.log", maxBytes=10 * 1024 * 1024, backupCount=5)
    )

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=log_handlers,
)

logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Run automatic migrations during startup and log lifecycle events."""
    init_db()
    logger.info("Database initialized successfully")
    try:
        yield
    finally:
        logger.info("Application shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/")
async def read_root() -> dict[str, str]:
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/api/docs",
    }


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}


app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
