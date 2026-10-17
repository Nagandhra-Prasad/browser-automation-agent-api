from datetime import UTC, datetime
from typing import Any

from bson import ObjectId

from app.database import get_database
from app.schemas.task import TaskStatus


class TaskRepository:
    def __init__(self) -> None:
        self._col = get_database().tasks

    @staticmethod
    def _serialize(doc: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(doc["_id"]),
            "user_id": doc["user_id"],
            "task_name": doc["task_name"],
            "command": doc["command"],
            "website": doc["website"],
            "status": doc["status"],
            "plan": doc.get("plan"),
            "created_at": doc["created_at"],
            "updated_at": doc["updated_at"],
        }

    async def create(
        self,
        user_id: str,
        task_name: str,
        command: str,
        website: str,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        doc = {
            "user_id": user_id,
            "task_name": task_name,
            "command": command,
            "website": website,
            "status": TaskStatus.PENDING.value,
            "plan": None,
            "created_at": now,
            "updated_at": now,
        }
        result = await self._col.insert_one(doc)
        doc["_id"] = result.inserted_id
        return self._serialize(doc)

    async def get_by_id(self, task_id: str, user_id: str | None = None) -> dict[str, Any] | None:
        if not ObjectId.is_valid(task_id):
            return None
        query: dict[str, Any] = {"_id": ObjectId(task_id)}
        if user_id:
            query["user_id"] = user_id
        doc = await self._col.find_one(query)
        return self._serialize(doc) if doc else None

    async def list_by_user(self, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        cursor = self._col.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
        return [self._serialize(doc) async for doc in cursor]

    async def count_all(self) -> int:
        return await self._col.count_documents({})

    async def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        plan: dict[str, Any] | None = None,
    ) -> None:
        update: dict[str, Any] = {
            "status": status.value,
            "updated_at": datetime.now(UTC),
        }
        if plan is not None:
            update["plan"] = plan
        await self._col.update_one({"_id": ObjectId(task_id)}, {"$set": update})
