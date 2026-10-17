from datetime import UTC, datetime
from typing import Any, Literal

from bson import ObjectId

from app.database import get_database

UserRole = Literal["user", "admin"]


class UserRepository:
    def __init__(self) -> None:
        self._col = get_database().users

    @staticmethod
    def _role(doc: dict[str, Any]) -> UserRole:
        role = doc.get("role", "user")
        return "admin" if role == "admin" else "user"

    @staticmethod
    def _is_active(doc: dict[str, Any]) -> bool:
        return bool(doc.get("is_active", True))

    @staticmethod
    def _serialize(doc: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(doc["_id"]),
            "name": doc["name"],
            "email": doc["email"],
            "role": UserRepository._role(doc),
            "onboarding_completed": bool(doc.get("onboarding_completed", False)),
            "is_active": UserRepository._is_active(doc),
            "password_hash": doc["password_hash"],
            "created_at": doc["created_at"],
        }

    @staticmethod
    def _serialize_public(doc: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(doc["_id"]),
            "name": doc["name"],
            "email": doc["email"],
            "role": UserRepository._role(doc),
            "onboarding_completed": bool(doc.get("onboarding_completed", False)),
            "is_active": UserRepository._is_active(doc),
            "created_at": doc["created_at"],
        }

    async def create(
        self,
        name: str,
        email: str,
        password_hash: str,
        role: UserRole = "user",
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        doc = {
            "name": name,
            "email": email.lower(),
            "password_hash": password_hash,
            "role": role,
            "onboarding_completed": False,
            "is_active": True,
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

    async def list_all(self, limit: int = 200) -> list[dict[str, Any]]:
        cursor = self._col.find().sort("created_at", -1).limit(limit)
        return [self._serialize_public(doc) async for doc in cursor]

    async def count_all(self) -> int:
        return await self._col.count_documents({})

    async def set_onboarding_completed(self, user_id: str) -> dict[str, Any] | None:
        if not ObjectId.is_valid(user_id):
            return None
        await self._col.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"onboarding_completed": True}},
        )
        return await self.get_by_id(user_id)

    async def set_active(self, user_id: str, is_active: bool) -> dict[str, Any] | None:
        if not ObjectId.is_valid(user_id):
            return None
        await self._col.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"is_active": is_active}},
        )
        return await self.get_by_id(user_id)
