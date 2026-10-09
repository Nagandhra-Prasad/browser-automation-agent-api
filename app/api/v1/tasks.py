from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user_id
from app.repositories.session_repository import SessionRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskCreate, TaskResponse, TaskStatus

router = APIRouter()


def _task_response(task: dict) -> TaskResponse:
    return TaskResponse(
        id=task["id"],
        user_id=task["user_id"],
        task_name=task["task_name"],
        command=task["command"],
        website=task["website"],
        status=TaskStatus(task["status"]),
        created_at=task["created_at"],
        updated_at=task["updated_at"],
    )


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    body: TaskCreate,
    user_id: str = Depends(get_current_user_id),
) -> TaskResponse:
    task = await TaskRepository().create(
        user_id=user_id,
        task_name=body.task_name,
        command=body.command,
        website=str(body.website),
    )
    return _task_response(task)


@router.get("", response_model=list[TaskResponse])
async def list_tasks(user_id: str = Depends(get_current_user_id)) -> list[TaskResponse]:
    tasks = await TaskRepository().list_by_user(user_id)
    return [_task_response(t) for t in tasks]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
) -> TaskResponse:
    task = await TaskRepository().get_by_id(task_id, user_id=user_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return _task_response(task)


@router.get("/{task_id}/sessions")
async def list_task_sessions(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
) -> list[dict]:
    task = await TaskRepository().get_by_id(task_id, user_id=user_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return await SessionRepository().list_by_task(task_id)
