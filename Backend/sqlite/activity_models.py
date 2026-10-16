from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from Backend.sqlite.database import Base


class ActivityLogModel(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    user_uid: Mapped[str] = mapped_column(
        String(128),
        index=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    role: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    action: Mapped[str] = mapped_column(
        String(50),
        index=True,
    )

    resource: Mapped[str] = mapped_column(
        String(100),
        index=True,
    )

    details: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )
