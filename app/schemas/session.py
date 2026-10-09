from datetime import datetime

from pydantic import BaseModel


class SessionResponse(BaseModel):
    id: str
    task_id: str
    start_time: datetime
    end_time: datetime | None
    status: str
