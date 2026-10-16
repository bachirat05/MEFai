from __future__ import annotations

from datetime import datetime

from sqlalchemy import Date, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from Backend.sqlite.database import Base


class LeaveRequestModel(Base):
    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    demande_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
    )

    user_uid: Mapped[str] = mapped_column(
        String(128),
        index=True,
    )
    employee_email: Mapped[str] = mapped_column(
    String(255),
    index=True,
    )

    employe_id: Mapped[str] = mapped_column(
        String(50),
        index=True,
    )

    type_conge: Mapped[str] = mapped_column(
        String(50),
    )

    date_debut: Mapped[datetime] = mapped_column(
        Date,
    )

    date_fin: Mapped[datetime] = mapped_column(
        Date,
    )

    motif: Mapped[str] = mapped_column(
        Text,
    )

    statut: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        index=True,
    )

    message: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )