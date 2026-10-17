from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user_id
from app.repositories.result_repository import ResultRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.schemas.result import ResultResponse
from app.schemas.result_feed import ResultTableRow
from app.services.result_feed_service import ResultFeedService

router = APIRouter()


def _result_response(row: dict) -> ResultResponse:
    return ResultResponse(
        id=row["id"],
        session_id=row["session_id"],
        task_id=row["task_id"],
        data=row["data"],
        summary=row.get("summary"),
        timestamp=row["timestamp"],
    )


@router.get("/table", response_model=list[ResultTableRow])
async def results_table(user_id: str = Depends(get_current_user_id)) -> list[ResultTableRow]:
    user = await UserRepository().get_by_id(user_id)
    is_admin = user and user.get("role") == "admin"
    return await ResultFeedService().table_for_user(user_id, admin=is_admin)


@router.get("/history", response_model=list[ResultResponse])
async def history(user_id: str = Depends(get_current_user_id)) -> list[ResultResponse]:
    tasks = await TaskRepository().list_by_user(user_id, limit=200)
    task_ids = [t["id"] for t in tasks]
    rows = await ResultRepository().list_by_user_tasks(task_ids)
    return [_result_response(r) for r in rows]


@router.get("/task/{task_id}", response_model=list[ResultResponse])
async def results_by_task(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
) -> list[ResultResponse]:
    task = await TaskRepository().get_by_id(task_id, user_id=user_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    rows = await ResultRepository().list_by_task(task_id)
    return [_result_response(r) for r in rows]


@router.get("/session/{session_id}", response_model=ResultResponse)
async def result_by_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
) -> ResultResponse:
    row = await ResultRepository().get_by_session(session_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")

    user = await UserRepository().get_by_id(user_id)
    is_admin = user and user.get("role") == "admin"
    task = await TaskRepository().get_by_id(row["task_id"], user_id=None if is_admin else user_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")

    return _result_response(row)
