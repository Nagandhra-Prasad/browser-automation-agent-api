from pydantic import BaseModel


class MessageResponse(BaseModel):
    message: str
    detail: str | None = None
