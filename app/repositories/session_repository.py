from datetime import UTC, datetime
from typing import Any

from bson import ObjectId

from app.database import get_database


class SessionRepository:
    def __init__(self) -> None:
        self._col = get_database().sessions

    @staticmethod
    def _serialize(doc: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(doc["_id"]),
            "task_id": doc["task_id"],
            "start_time": doc["start_time"],
            "end_time": doc.get("end_time"),
            "status": doc["status"],
        }

    async def create(self, task_id: str) -> dict[str, Any]:
        now = datetime.now(UTC)
        doc = {
            "task_id": task_id,
            "start_time": now,
            "end_time": None,
            "status": "running",
        }
        result = await self._col.insert_one(doc)
        doc["_id"] = result.inserted_id
        return self._serialize(doc)

    async def complete(self, session_id: str, status: str) -> None:
        await self._col.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"end_time": datetime.now(UTC), "status": status}},
        )

    async def list_by_task(self, task_id: str) -> list[dict[str, Any]]:
        cursor = self._col.find({"task_id": task_id}).sort("start_time", -1)
        return [self._serialize(doc) async for doc in cursor]
