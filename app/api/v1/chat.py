from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user_id
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.result_repository import ResultRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.conversation import (
    ConversationCreateRequest,
    ConversationDetailResponse,
    ConversationResponse,
    StoredMessageResponse,
)
from app.schemas.job import JobListing
from app.services.automation_orchestrator import AutomationOrchestrator
from app.services.chat_intent import ChatIntent, ChatIntentService
from app.services.chat_persistence import ChatPersistenceService
from app.services.job_search import JobSearchService
from app.services.playwright_check import chromium_install_hint, is_chromium_ready

router = APIRouter()


def _jobs_from_data(data: dict | None) -> list[JobListing]:
    if not data:
        return []
    raw = data.get("jobs") or []
    return [JobListing.model_validate(j) for j in raw]


def _conversation_response(row: dict) -> ConversationResponse:
    return ConversationResponse(
        id=row["id"],
        user_id=row["user_id"],
        title=row["title"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _message_response(row: dict) -> StoredMessageResponse:
    return StoredMessageResponse(
        id=row["id"],
        conversation_id=row["conversation_id"],
        role=row["role"],
        content=row["content"],
        metadata=row.get("metadata"),
        created_at=row["created_at"],
    )


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(user_id: str = Depends(get_current_user_id)) -> list[ConversationResponse]:
    user = await UserRepository().get_by_id(user_id)
    repo = ConversationRepository()
    if user and user.get("role") == "admin":
        rows = await repo.list_all()
    else:
        rows = await repo.list_by_user(user_id)
    return [_conversation_response(r) for r in rows]


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    body: ConversationCreateRequest,
    user_id: str = Depends(get_current_user_id),
) -> ConversationResponse:
    row = await ConversationRepository().create(user_id, body.title)
    return _conversation_response(row)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    user_id: str = Depends(get_current_user_id),
) -> ConversationDetailResponse:
    user = await UserRepository().get_by_id(user_id)
    is_admin = user and user.get("role") == "admin"
    conv = await ConversationRepository().get_by_id(
        conversation_id,
        user_id=None if is_admin else user_id,
    )
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    messages = await MessageRepository().list_by_conversation(
        conversation_id,
        user_id=None if is_admin else user_id,
    )
    return ConversationDetailResponse(
        conversation=_conversation_response(conv),
        messages=[_message_response(m) for m in messages],
    )


@router.post("", response_model=ChatResponse)
async def chat_with_agent(
    body: ChatRequest,
    user_id: str = Depends(get_current_user_id),
) -> ChatResponse:
    message = body.message.strip()
    persistence = ChatPersistenceService()
    conversation = await persistence.resolve_conversation(user_id, body.conversation_id, message)
    conversation_id = conversation["id"]

    await persistence.save_user_message(conversation_id, user_id, message)

    intent_service = ChatIntentService()
    intent = intent_service.detect(message)

    user = await UserRepository().get_by_id(user_id)
    user_name = user["name"] if user else None

    if intent == ChatIntent.GREETING:
        response = ChatResponse(
            conversation_id=conversation_id,
            reply=intent_service.greeting_reply(user_name),
            status="conversation",
            intent=intent.value,
        )
        await persistence.save_agent_message(conversation_id, user_id, response)
        return response

    if intent == ChatIntent.HELP:
        response = ChatResponse(
            conversation_id=conversation_id,
            reply=intent_service.help_reply(),
            status="conversation",
            intent=intent.value,
        )
        await persistence.save_agent_message(conversation_id, user_id, response)
        return response

    if intent == ChatIntent.SMALL_TALK:
        response = ChatResponse(
            conversation_id=conversation_id,
            reply=intent_service.small_talk_reply(),
            status="conversation",
            intent=intent.value,
        )
        await persistence.save_agent_message(conversation_id, user_id, response)
        return response

    if not await is_chromium_ready():
        response = ChatResponse(
            conversation_id=conversation_id,
            reply=chromium_install_hint(),
            status="failed",
            intent=intent.value,
        )
        await persistence.save_agent_message(conversation_id, user_id, response)
        return response

    website = str(body.website) if body.website else JobSearchService.build_search_url(message)
    task_name = message[:80] or "Job search"
    task = await TaskRepository().create(
        user_id=user_id,
        task_name=task_name,
        command=message,
        website=website,
    )

    run = await AutomationOrchestrator().run_task(
        task["id"],
        user_id,
        headless=body.headless,
    )

    summary = None
    data = None
    jobs: list[JobListing] = []
    if run.result_id:
        await ResultRepository().attach_conversation(run.result_id, conversation_id)
        result = await ResultRepository().get_by_session(run.session_id)
        if result:
            summary = result.get("summary")
            data = result.get("data")
            jobs = _jobs_from_data(data)

    if run.status == "completed":
        if jobs:
            reply = summary or f"Found {len(jobs)} job listing(s). See the table below."
        else:
            reply = (
                "Search finished but no job rows could be parsed. "
                "Try a clearer query like: Java developer jobs in Chennai. "
                "If this keeps happening, set PLAYWRIGHT_HEADLESS=false in .env and retry."
            )
    else:
        err = run.message
        if "Executable doesn't exist" in err or "playwright" in err.lower():
            err = f"{err}\n\n{chromium_install_hint()}"
        reply = f"Automation failed: {err}"

    response = ChatResponse(
        conversation_id=conversation_id,
        reply=reply,
        status=run.status,
        intent=intent.value,
        task_id=run.task_id,
        session_id=run.session_id,
        result_id=run.result_id,
        summary=summary,
        data=data,
        plan=run.plan,
        jobs=jobs,
        source_website=JobSearchService.label_for_url(website),
    )
    await persistence.save_agent_message(conversation_id, user_id, response)
    return response
