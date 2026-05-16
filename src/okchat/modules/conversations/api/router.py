"""
OkChat — Conversations API Router
Thin controller: validates HTTP, calls use cases, returns responses.
No business logic here. All logic lives in use cases.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from okchat.infrastructure.database.session import get_db
from okchat.infrastructure.events.bus import event_bus
from okchat.modules.conversations.application.use_cases.send_message import (
    SendMessageInput,
    SendMessageUseCase,
)
from okchat.modules.conversations.api.dependencies import (
    get_conversation_repository,
    get_current_user,
    get_llm_provider,
)

router = APIRouter()


# ── Request / Response Schemas ────────────────────────────────────────────────


class CreateConversationRequest(BaseModel):
    channel: str = Field(default="web", pattern="^(web|whatsapp|telegram|discord|voice)$")
    system_prompt: str | None = Field(default=None, max_length=4096)


class ConversationResponse(BaseModel):
    id: UUID
    channel: str
    status: str
    created_at: str


class SendMessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=32_000)
    stream: bool = Field(default=False)


class SendMessageResponse(BaseModel):
    conversation_id: UUID
    message_id: UUID
    assistant_text: str
    tokens_used: int | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post(
    "/",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation",
)
async def create_conversation(
    body: CreateConversationRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    repo=Depends(get_conversation_repository),
) -> ConversationResponse:
    from okchat.modules.conversations.domain.entities import Conversation

    conversation = Conversation.create(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        channel=body.channel,
        system_prompt=body.system_prompt,
    )
    saved = await repo.save(conversation)

    return ConversationResponse(
        id=saved.id,
        channel=saved.channel,
        status=saved.status,
        created_at=saved.created_at.isoformat(),
    )


@router.post(
    "/{conversation_id}/messages",
    response_model=SendMessageResponse,
    summary="Send a message and receive an AI response",
)
async def send_message(
    conversation_id: UUID,
    body: SendMessageRequest,
    current_user=Depends(get_current_user),
    repo=Depends(get_conversation_repository),
    llm=Depends(get_llm_provider),
) -> SendMessageResponse:
    use_case = SendMessageUseCase(
        repository=repo,
        llm=llm,
        event_bus=event_bus,
    )

    result = await use_case.execute(
        SendMessageInput(
            conversation_id=conversation_id,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            text=body.text,
            stream=body.stream,
        )
    )

    return SendMessageResponse(
        conversation_id=result.conversation_id,
        message_id=result.message_id,
        assistant_text=result.assistant_text,
        tokens_used=result.tokens_used,
    )


@router.get(
    "/{conversation_id}",
    summary="Get conversation details",
)
async def get_conversation(
    conversation_id: UUID,
    current_user=Depends(get_current_user),
    repo=Depends(get_conversation_repository),
) -> ConversationResponse:
    conversation = await repo.get_by_id(conversation_id)
    if not conversation or conversation.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    return ConversationResponse(
        id=conversation.id,
        channel=conversation.channel,
        status=conversation.status,
        created_at=conversation.created_at.isoformat(),
    )
