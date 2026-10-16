from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"] = Field(
        ...,
        description="user ou assistant",
        examples=["user"],
    )
    content: str = Field(
        ...,
        min_length=1,
        examples=["Quel est le délai de congé ?"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "role": "user",
                    "content": "Quel est le délai de congé ?",
                }
            ]
        }
    )


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        examples=["Quel est le délai de congé ?"],
    )
    conversation_id: int | None = Field(
        default=None,
        examples=[12],
        description=(
            "Identifiant retourné par GET /api/conversations "
            "ou POST /api/conversations. Laisser null pour créer "
            "une nouvelle conversation."
        ),
    )
    history: list[ChatMessage] = Field(default_factory=list)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "message": "Quel est le délai de congé ?",
                    "conversation_id": 12,
                    "history": [],
                }
            ]
        }
    )


class ChatResponse(BaseModel):
    answer: str = Field(
        examples=[
            "Le délai de congé dépend de la politique RH applicable."
        ]
    )
    tools_used: list[str] = Field(default_factory=list)
    conversation_id: int = Field(examples=[12])

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "answer": (
                        "Le délai de congé dépend de la politique RH "
                        "applicable."
                    ),
                    "tools_used": ["search_documents"],
                    "conversation_id": 12,
                }
            ]
        }
    )


class ChatMessageResponse(BaseModel):
    id: int = Field(examples=[34])
    role: Literal["user", "assistant"] = Field(examples=["user"])
    content: str = Field(examples=["Quel est le délai de congé ?"])
    created_at: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 34,
                    "role": "user",
                    "content": "Quel est le délai de congé ?",
                    "created_at": "2026-08-16T10:15:00Z",
                }
            ]
        }
    )


class ConversationResponse(BaseModel):
    id: int = Field(examples=[12])
    title: str = Field(examples=["Questions RH"])
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessageResponse] = Field(default_factory=list)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 12,
                    "title": "Questions RH",
                    "created_at": "2026-08-16T10:12:00Z",
                    "updated_at": "2026-08-16T10:15:00Z",
                    "messages": [
                        {
                            "id": 34,
                            "role": "user",
                            "content": "Quel est le délai de congé ?",
                            "created_at": "2026-08-16T10:15:00Z",
                        },
                        {
                            "id": 35,
                            "role": "assistant",
                            "content": (
                                "Le délai de congé dépend de la "
                                "politique RH applicable."
                            ),
                            "created_at": "2026-08-16T10:15:03Z",
                        },
                    ],
                }
            ]
        }
    )


class ConversationSummaryResponse(BaseModel):
    id: int = Field(examples=[12])
    title: str = Field(examples=["Questions RH"])
    created_at: datetime
    updated_at: datetime
    message_count: int = Field(examples=[2])

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 12,
                    "title": "Questions RH",
                    "created_at": "2026-08-16T10:12:00Z",
                    "updated_at": "2026-08-16T10:15:00Z",
                    "message_count": 2,
                }
            ]
        }
    )


class ConversationDeleteResponse(BaseModel):
    message: str = Field(examples=["Conversation supprimée"])
    conversation_id: int = Field(examples=[12])

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "message": "Conversation supprimée",
                    "conversation_id": 12,
                }
            ]
        }
    )
