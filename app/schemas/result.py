from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ResultResponse(BaseModel):
    id: str
    session_id: str
    task_id: str
    data: dict[str, Any]
    summary: str | None
    timestamp: datetime
