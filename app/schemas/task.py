from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class TaskStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskCreate(BaseModel):
    task_name: str = Field(min_length=1, max_length=200)
    command: str = Field(
        min_length=3,
        max_length=2000,
        description="Natural language command, e.g. Find Java jobs in Chennai",
    )
    website: HttpUrl = Field(description="Target website URL to automate")


class TaskResponse(BaseModel):
    id: str
    user_id: str
    task_name: str
    command: str
    website: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
