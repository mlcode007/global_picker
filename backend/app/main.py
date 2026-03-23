import logging
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.api.v1 import router as v1_router

settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def _startup_recover():
    """恢复服务重启前中断的拍照购任务，并重新调度执行。"""
    from app.database import SessionLocal
    from app.services import photo_search_service
    from app.workers.pdd_photo.worker import execute_photo_search_task

    db = SessionLocal()
    try:
        recovered = photo_search_service.recover_interrupted_tasks(db)
        if not recovered:
            return

        tasks = db.query(photo_search_service.PhotoSearchTask).filter(
            photo_search_service.PhotoSearchTask.status == "queued"
        ).order_by(photo_search_service.PhotoSearchTask.created_at.desc()).limit(1).all()

        for task in tasks:
            logger.info("Re-dispatching recovered task #%d", task.id)
            threading.Thread(
                target=execute_photo_search_task,
                args=(task.id,),
                daemon=True,
            ).start()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Global Picker API 启动 (env=%s)", settings.APP_ENV)
    _startup_recover()
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

# 暴露 artifacts 目录为静态文件服务，前端可通过 /artifacts/... 访问截图
from pathlib import Path as _Path
_artifacts_dir = _Path("/Users/smzdm/global_picker/artifacts")
_artifacts_dir.mkdir(parents=True, exist_ok=True)
app.mount("/artifacts", StaticFiles(directory=str(_artifacts_dir)), name="artifacts")


@app.get("/health", tags=["系统"])
def health_check():
    return {"status": "ok", "env": settings.APP_ENV}
