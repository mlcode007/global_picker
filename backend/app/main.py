import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.v1 import router as v1_router

settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Global Picker API 启动 (env=%s)", settings.APP_ENV)
    yield
    logger.info("Global Picker API 关闭")


app = FastAPI(
    title="Global Picker API",
    description="跨平台选品比价系统 - TikTok Shop vs 拼多多",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)


@app.get("/health", tags=["系统"])
def health_check():
    return {"status": "ok", "env": settings.APP_ENV}
