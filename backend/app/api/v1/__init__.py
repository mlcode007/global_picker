from fastapi import APIRouter
from app.api.v1 import products, pdd, profit, export, auth, tasks, settings, photo_search, dashboard

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(products.router)
router.include_router(pdd.router)
router.include_router(profit.router)
router.include_router(export.router)
router.include_router(tasks.router)
router.include_router(settings.router)
router.include_router(photo_search.router)
router.include_router(dashboard.router)
