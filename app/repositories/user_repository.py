from datetime import UTC, datetime
from typing import Any

from bson import ObjectId

from app.database import get_database


class UserRepository:
    def __init__(self) -> None:
        self._col = get_database().users

    @staticmethod
    def _serialize(doc: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(doc["_id"]),
            "name": doc["name"],
            "email": doc["email"],
            "password_hash": doc["password_hash"],
            "created_at": doc["created_at"],
        }

    async def create(self, name: str, email: str, password_hash: str) -> dict[str, Any]:
        now = datetime.now(UTC)
        doc = {
            "name": name,
            "email": email.lower(),
            "password_hash": password_hash,
            "created_at": now,
        }
        result = await self._col.insert_one(doc)
        doc["_id"] = result.inserted_id
        return self._serialize(doc)

    async def get_by_email(self, email: str) -> dict[str, Any] | None:
        doc = await self._col.find_one({"email": email.lower()})
        return self._serialize(doc) if doc else None

    async def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        if not ObjectId.is_valid(user_id):
            return None
        doc = await self._col.find_one({"_id": ObjectId(user_id)})
        return self._serialize(doc) if doc else None
