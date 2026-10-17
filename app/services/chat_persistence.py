from typing import Any

from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.schemas.chat import ChatResponse


class ChatPersistenceService:
    def __init__(self) -> None:
        self._conversations = ConversationRepository()
        self._messages = MessageRepository()

    async def resolve_conversation(
        self,
        user_id: str,
        conversation_id: str | None,
        first_message: str,
    ) -> dict[str, Any]:
        if conversation_id:
            existing = await self._conversations.get_by_id(conversation_id, user_id)
            if existing:
                return existing
        title = first_message.strip()[:80] or "New conversation"
        return await self._conversations.create(user_id, title)

    async def save_user_message(
        self,
        conversation_id: str,
        user_id: str,
        content: str,
    ) -> dict[str, Any]:
        msg = await self._messages.create(conversation_id, user_id, "user", content)
        await self._conversations.touch(conversation_id)
        return msg

    async def save_agent_message(
        self,
        conversation_id: str,
        user_id: str,
        response: ChatResponse,
    ) -> dict[str, Any]:
        metadata = response.model_dump()
        metadata.pop("reply", None)
        msg = await self._messages.create(
            conversation_id,
            user_id,
            "agent",
            response.reply,
            metadata=metadata,
        )
        await self._conversations.touch(conversation_id)
        return msg
