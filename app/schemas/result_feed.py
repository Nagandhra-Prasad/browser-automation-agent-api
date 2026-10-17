from datetime import datetime

from pydantic import BaseModel

from app.schemas.job import JobListing


class ResultTableRow(BaseModel):
    id: str
    task_id: str
    session_id: str
    conversation_id: str | None = None
    user_id: str | None = None
    user_name: str | None = None
    user_email: str | None = None
    task_name: str | None = None
    command: str | None = None
    website: str | None = None
    summary: str | None = None
    job_count: int = 0
    jobs: list[JobListing] = []
    timestamp: datetime
