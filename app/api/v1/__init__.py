from fastapi import APIRouter

from app.api.v1 import auth, automation, chat, dashboard, health, reports, results, tasks, users

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(automation.router, prefix="/automation", tags=["automation"])
api_router.include_router(results.router, prefix="/results", tags=["results"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
