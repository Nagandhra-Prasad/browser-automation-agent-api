import logging
from contextlib import asynccontextmanager

from app.playwright_env import configure_playwright_env

configure_playwright_env()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.config import get_settings
from app.database import close_mongo_connection, ensure_indexes
from app.services.llm_client import log_llm_startup_status
from app.services.playwright_bootstrap import ensure_chromium_installed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    configure_playwright_env(settings.playwright_browsers_path or None)
    await ensure_indexes()
    log_llm_startup_status()
    await ensure_chromium_installed()
    logger.info("Application started")
    yield
    await close_mongo_connection()
    logger.info("Application shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
