from datetime import UTC, datetime
from typing import Any, Literal

from bson import ObjectId

from app.database import get_database

MessageRole = Literal["user", "agent", "system"]


class MessageRepository:
    def __init__(self) -> None:
        self._col = get_database().messages

    @staticmethod
    def _serialize(doc: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(doc["_id"]),
            "conversation_id": doc["conversation_id"],
            "user_id": doc["user_id"],
            "role": doc["role"],
            "content": doc["content"],
            "metadata": doc.get("metadata"),
            "created_at": doc["created_at"],
        }

    async def create(
        self,
        conversation_id: str,
        user_id: str,
        role: MessageRole,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        doc = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "role": role,
            "content": content,
            "metadata": metadata,
            "created_at": now,
        }
        result = await self._col.insert_one(doc)
        doc["_id"] = result.inserted_id
        return self._serialize(doc)

    async def list_by_conversation(
        self,
        conversation_id: str,
        user_id: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {"conversation_id": conversation_id}
        if user_id:
            query["user_id"] = user_id
        cursor = self._col.find(query).sort("created_at", 1).limit(limit)
        return [self._serialize(doc) async for doc in cursor]
