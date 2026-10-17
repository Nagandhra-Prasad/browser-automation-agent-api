from datetime import UTC, datetime
from typing import Any

from bson import ObjectId

from app.database import get_database


class ConversationRepository:
    def __init__(self) -> None:
        self._col = get_database().conversations

    @staticmethod
    def _serialize(doc: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(doc["_id"]),
            "user_id": doc["user_id"],
            "title": doc["title"],
            "created_at": doc["created_at"],
            "updated_at": doc["updated_at"],
        }

    async def create(self, user_id: str, title: str) -> dict[str, Any]:
        now = datetime.now(UTC)
        doc = {
            "user_id": user_id,
            "title": title[:120] or "New conversation",
            "created_at": now,
            "updated_at": now,
        }
        result = await self._col.insert_one(doc)
        doc["_id"] = result.inserted_id
        return self._serialize(doc)

    async def get_by_id(self, conversation_id: str, user_id: str | None = None) -> dict[str, Any] | None:
        if not ObjectId.is_valid(conversation_id):
            return None
        query: dict[str, Any] = {"_id": ObjectId(conversation_id)}
        if user_id:
            query["user_id"] = user_id
        doc = await self._col.find_one(query)
        return self._serialize(doc) if doc else None

    async def list_by_user(self, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        cursor = self._col.find({"user_id": user_id}).sort("updated_at", -1).limit(limit)
        return [self._serialize(doc) async for doc in cursor]

    async def list_all(self, limit: int = 200) -> list[dict[str, Any]]:
        cursor = self._col.find().sort("updated_at", -1).limit(limit)
        return [self._serialize(doc) async for doc in cursor]

    async def touch(self, conversation_id: str) -> None:
        await self._col.update_one(
            {"_id": ObjectId(conversation_id)},
            {"$set": {"updated_at": datetime.now(UTC)}},
        )
