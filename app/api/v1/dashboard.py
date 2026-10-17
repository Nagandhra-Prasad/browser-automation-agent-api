from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user_id
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.schemas.dashboard import DashboardSummary

router = APIRouter()


@router.get("/summary", response_model=DashboardSummary)
async def dashboard_summary(user_id: str = Depends(get_current_user_id)) -> DashboardSummary:
    user_repo = UserRepository()
    task_repo = TaskRepository()
    user = await user_repo.get_by_id(user_id)
    if not user:
        return DashboardSummary(role="user", my_tasks=0)

    my_tasks = len(await task_repo.list_by_user(user_id, limit=500))
    role = user["role"]

    if role == "admin":
        return DashboardSummary(
            role="admin",
            my_tasks=my_tasks,
            total_users=await user_repo.count_all(),
            total_tasks=await task_repo.count_all(),
        )

    return DashboardSummary(role="user", my_tasks=my_tasks)
