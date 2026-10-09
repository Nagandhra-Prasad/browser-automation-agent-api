from datetime import UTC, datetime
from typing import Any

from bson import ObjectId

from app.database import get_database


class ResultRepository:
    def __init__(self) -> None:
        self._col = get_database().results

    @staticmethod
    def _serialize(doc: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(doc["_id"]),
            "session_id": doc["session_id"],
            "task_id": doc["task_id"],
            "data": doc["data"],
            "summary": doc.get("summary"),
            "timestamp": doc["timestamp"],
        }

    async def create(
        self,
        session_id: str,
        task_id: str,
        data: dict[str, Any],
        summary: str | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        doc = {
            "session_id": session_id,
            "task_id": task_id,
            "data": data,
            "summary": summary,
            "timestamp": now,
        }
        result = await self._col.insert_one(doc)
        doc["_id"] = result.inserted_id
        return self._serialize(doc)

    async def get_by_session(self, session_id: str) -> dict[str, Any] | None:
        doc = await self._col.find_one({"session_id": session_id})
        return self._serialize(doc) if doc else None

    async def list_by_task(self, task_id: str) -> list[dict[str, Any]]:
        cursor = self._col.find({"task_id": task_id}).sort("timestamp", -1)
        return [self._serialize(doc) async for doc in cursor]

    async def list_by_user_tasks(self, task_ids: list[str]) -> list[dict[str, Any]]:
        if not task_ids:
            return []
        cursor = self._col.find({"task_id": {"$in": task_ids}}).sort("timestamp", -1)
        return [self._serialize(doc) async for doc in cursor]
