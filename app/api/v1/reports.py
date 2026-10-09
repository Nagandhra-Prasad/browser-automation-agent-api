import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from app.core.dependencies import get_current_user_id
from app.repositories.result_repository import ResultRepository
from app.repositories.task_repository import TaskRepository

router = APIRouter()


@router.get("/task/{task_id}/download")
async def download_task_report(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
) -> Response:
    task = await TaskRepository().get_by_id(task_id, user_id=user_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    results = await ResultRepository().list_by_task(task_id)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "task": {
            "id": task["id"],
            "task_name": task["task_name"],
            "command": task["command"],
            "website": task["website"],
            "status": task["status"],
        },
        "results": results,
    }
    content = json.dumps(payload, indent=2, default=str)
    filename = f"report_{task_id}.json"
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
