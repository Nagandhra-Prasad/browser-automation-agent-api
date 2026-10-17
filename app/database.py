from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import get_settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncIOMotorClient(settings.mongodb_url)
    return _client


def get_database() -> AsyncIOMotorDatabase:
    settings = get_settings()
    return get_client()[settings.mongodb_db_name]


async def close_mongo_connection() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


async def ensure_indexes() -> None:
    db = get_database()
    await db.users.create_index("email", unique=True)
    await db.tasks.create_index([("user_id", 1), ("created_at", -1)])
    await db.sessions.create_index([("task_id", 1), ("start_time", -1)])
    await db.results.create_index([("session_id", 1)])
    await db.conversations.create_index([("user_id", 1), ("updated_at", -1)])
    await db.messages.create_index([("conversation_id", 1), ("created_at", 1)])
    await db.messages.create_index([("user_id", 1), ("created_at", -1)])
