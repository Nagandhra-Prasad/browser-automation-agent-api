from fastapi import APIRouter

from app.api.v1 import auth, automation, health, reports, results, tasks

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(automation.router, prefix="/automation", tags=["automation"])
api_router.include_router(results.router, prefix="/results", tags=["results"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
