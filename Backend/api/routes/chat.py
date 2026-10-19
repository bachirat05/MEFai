from __future__ import annotations

import logging
from contextlib import AsyncExitStack
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.firebase_auth import verify_firebase_token
from Backend.sqlite.chat_models import ChatMessageModel, ConversationModel
from Backend.sqlite.database import get_db
from schemas.chat import (
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    ConversationDeleteResponse,
    ConversationResponse,
    ConversationSummaryResponse,
)
from services.audit.activity_log_service import (
    CHAT_MESSAGE,
    safe_log_activity,
)
from services.chat.chat_service import chat_service

from Backend.services.mcp.mcp_client import MCPClient



logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api",
    tags=["chat"],
)


mcp_client = MCPClient(
    server_url="http://127.0.0.1:8000/mcp/sse"
)


def _user_uid(user: dict) -> str:
    uid = str(user.get("uid") or "")

    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur Firebase invalide",
        )

    return uid


def _title_from_message(message: str) -> str:
    normalized = " ".join(
        message.strip().split()
    )

    if not normalized:
        return "Nouvelle conversation"

    if len(normalized) <= 60:
        return normalized

    return f"{normalized[:57].rstrip()}..."


def _get_owned_conversation(
    db: Session,
    *,
    conversation_id: int,
    user_uid: str,
) -> ConversationModel:
    conversation = (
        db.query(ConversationModel)
        .filter(
            ConversationModel.id == conversation_id,
            ConversationModel.user_uid == user_uid,
        )
        .first()
    )

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation introuvable",
        )

    return conversation


def _message_response(
    message: ChatMessageModel,
) -> ChatMessageResponse:
    return ChatMessageResponse(
        id=message.id,
        role=message.role,
        content=message.content,
        created_at=message.created_at,
    )


def _conversation_response(
    conversation: ConversationModel,
) -> ConversationResponse:
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[
            _message_response(message)
            for message in conversation.messages
        ],
    )


def _conversation_summary(
    conversation: ConversationModel,
) -> ConversationSummaryResponse:
    return ConversationSummaryResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=len(conversation.messages),
    )


@router.get(
    "/conversations",
    response_model=list[ConversationSummaryResponse],
)
async def list_conversations(
    user=Depends(verify_firebase_token),
    db: Session = Depends(get_db),
) -> list[ConversationSummaryResponse]:
    uid = _user_uid(user)

    conversations = (
        db.query(ConversationModel)
        .filter(ConversationModel.user_uid == uid)
        .order_by(
            ConversationModel.updated_at.desc(),
            ConversationModel.id.desc(),
        )
        .all()
    )

    return [
        _conversation_summary(conversation)
        for conversation in conversations
    ]


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    user=Depends(verify_firebase_token),
    db: Session = Depends(get_db),
) -> ConversationResponse:
    uid = _user_uid(user)

    conversation = ConversationModel(
        user_uid=uid,
        title="Nouvelle conversation",
    )

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return _conversation_response(conversation)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
)
async def get_conversation(
    conversation_id: int,
    user=Depends(verify_firebase_token),
    db: Session = Depends(get_db),
) -> ConversationResponse:
    conversation = _get_owned_conversation(
        db,
        conversation_id=conversation_id,
        user_uid=_user_uid(user),
    )

    return _conversation_response(conversation)


@router.delete(
    "/conversations/{conversation_id}",
    response_model=ConversationDeleteResponse,
)
async def delete_conversation(
    conversation_id: int,
    user=Depends(verify_firebase_token),
    db: Session = Depends(get_db),
) -> ConversationDeleteResponse:
    conversation = _get_owned_conversation(
        db,
        conversation_id=conversation_id,
        user_uid=_user_uid(user),
    )

    db.delete(conversation)
    db.commit()

    return ConversationDeleteResponse(
        message="Conversation supprimée",
        conversation_id=conversation_id,
    )


@router.post(
    "/chat",
    response_model=ChatResponse,
)
async def chat(
    request: ChatRequest,
    user=Depends(verify_firebase_token),
    db: Session = Depends(get_db),
) -> ChatResponse:
    uid = _user_uid(user)
    text = request.message.strip()

    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le message ne peut pas être vide.",
        )

    try:
        if request.conversation_id is None:
            conversation = ConversationModel(
                user_uid=uid,
                title=_title_from_message(text),
            )
            db.add(conversation)
            db.flush()
        else:
            conversation = _get_owned_conversation(
                db,
                conversation_id=request.conversation_id,
                user_uid=uid,
            )

            if not conversation.messages:
                conversation.title = _title_from_message(text)

        history = [
            {
                "role": message.role,
                "content": message.content,
            }
            for message in conversation.messages
        ]

        db.add(
            ChatMessageModel(
                conversation_id=conversation.id,
                role="user",
                content=text,
            )
        )
        conversation.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(conversation)

        async with AsyncExitStack() as stack:
            tools = await mcp_client.get_tools(
                stack,
                authenticated_user=user,
            )

            result = await chat_service.run_agent(
                message=text,
                tools=tools,
                history=history,
            )

        answer = str(result.get("answer") or "").strip()
        tools_used = list(result.get("tools_used") or [])

        if not answer:
            answer = (
                "Les documents internes actuels "
                "ne précisent pas cette information."
            )

        db.add(
            ChatMessageModel(
                conversation_id=conversation.id,
                role="assistant",
                content=answer,
            )
        )
        conversation.updated_at = datetime.utcnow()
        db.commit()

        safe_log_activity(
            db,
            user=user,
            action=CHAT_MESSAGE,
            resource="chat",
            details={
                "message_length": len(text),
                "conversation_id": conversation.id,
            },
        )

        return ChatResponse(
            answer=answer,
            tools_used=tools_used,
            conversation_id=conversation.id,
        )

    except HTTPException:
        db.rollback()
        raise

    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        db.rollback()
        logger.exception(
            "Chat request failed"
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors du traitement de la demande.",
        ) from exc
