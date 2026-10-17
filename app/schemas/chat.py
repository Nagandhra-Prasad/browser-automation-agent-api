from typing import Any

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.job import JobListing


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = Field(
        default=None,
        description="Existing conversation; created automatically if omitted",
    )
    website: HttpUrl | None = Field(
        default=None,
        description="Optional; agent picks a job search site when omitted",
    )
    headless: bool = True


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
    status: str
    intent: str
    task_id: str | None = None
    session_id: str | None = None
    result_id: str | None = None
    summary: str | None = None
    data: dict[str, Any] | None = None
    plan: dict[str, Any] | None = None
    jobs: list[JobListing] = Field(default_factory=list)
    source_website: str | None = None
