from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from Backend.sqlite.database import Base


class ConversationModel(Base):
    __tablename__ = "chat_conversations"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    user_uid: Mapped[str] = mapped_column(
        String(128),
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(120),
        default="Nouvelle conversation",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )

    messages: Mapped[list["ChatMessageModel"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ChatMessageModel.created_at",
    )


class ChatMessageModel(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("chat_conversations.id"),
        index=True,
    )

    role: Mapped[str] = mapped_column(
        String(20),
    )

    content: Mapped[str] = mapped_column(
        Text,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )

    conversation: Mapped[ConversationModel] = relationship(
        back_populates="messages",
    )
