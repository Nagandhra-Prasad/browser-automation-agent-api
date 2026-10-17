from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.job import JobListing


class ConversationResponse(BaseModel):
    id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime


class StoredMessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: Literal["user", "agent", "system"]
    content: str
    metadata: dict[str, Any] | None = None
    created_at: datetime


class ConversationDetailResponse(BaseModel):
    conversation: ConversationResponse
    messages: list[StoredMessageResponse]


class ConversationCreateRequest(BaseModel):
    title: str = Field(default="New conversation", max_length=120)
