from __future__ import annotations

from datetime import datetime, time
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.firebase_auth import require_admin
from core.config import get_settings
from Backend.sqlite.database import get_db
from services.audit.activity_log_service import (
    get_audit_logs,
    get_activity_summary,
)


router = APIRouter(
    prefix="/api/admin",
    tags=["admin-system"],
)

settings = get_settings()

ROOT_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
    .parent
)

DOCUMENTS_DIR = (
    ROOT_DIR
    / "data"
    / "documents"
)

SUPPORTED_EXTENSIONS = {
    ".txt",
    ".pdf",
    ".docx",
}


@router.get("/system-status")
async def get_system_status(
    user=Depends(require_admin),
):
    # -----------------------------
    # Documents
    # -----------------------------

    document_count = 0

    if DOCUMENTS_DIR.exists():
        document_count = sum(
            1
            for file_path in DOCUMENTS_DIR.iterdir()
            if (
                file_path.is_file()
                and file_path.suffix.lower()
                in SUPPORTED_EXTENSIONS
            )
        )

    # -----------------------------
    # Ollama
    # -----------------------------

    ollama_online = False

    try:
        async with httpx.AsyncClient(
            timeout=3.0
        ) as client:
            response = await client.get(
                f"{settings.ollama_base_url}/api/tags"
            )

            ollama_online = (
                response.status_code == 200
            )

    except Exception:
        ollama_online = False

    # -----------------------------
    # RAG
    # -----------------------------

    rag_ready = (
        Path(
            settings.chroma_persist_dir
        ).exists()
    )

    # -----------------------------
    # n8n
    # -----------------------------

    n8n_configured = bool(
        settings.n8n_webhook_url
    )

    return {
        "ollama": (
            "online"
            if ollama_online
            else "offline"
        ),

        "rag": (
            "ready"
            if rag_ready
            else "unavailable"
        ),

        "n8n": (
            "configured"
            if n8n_configured
            else "not_configured"
        ),

        "documents": document_count,

        "embedding_model":
            settings.ollama_embedding_model,

        "rag_collection":
            settings.chroma_collection_name,
    }


@router.get("/activity")
async def get_admin_activity(
    days: int = 7,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return get_activity_summary(
        db,
        days=days,
    )


def _parse_audit_datetime(
    value: str | None,
    *,
    end_of_day: bool = False,
) -> datetime | None:
    if not value:
        return None

    normalized = value.strip()

    try:
        if "T" not in normalized and " " not in normalized:
            parsed_date = datetime.fromisoformat(normalized).date()
            return datetime.combine(
                parsed_date,
                time.max if end_of_day else time.min,
            )

        return datetime.fromisoformat(
            normalized.replace(
                "Z",
                "+00:00",
            )
        ).replace(tzinfo=None)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=(
                "Format de date invalide. "
                "Utilisez YYYY-MM-DD ou une datetime ISO."
            ),
        ) from exc


@router.get("/audit-logs")
async def get_admin_audit_logs(
    page: int = 1,
    page_size: int = 20,
    action: str | None = None,
    role: str | None = None,
    resource: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    user_search: str | None = Query(
        default=None,
        alias="user",
    ),
    admin_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return get_audit_logs(
        db,
        page=page,
        page_size=page_size,
        action=action,
        role=role,
        resource=resource,
        user=user_search,
        date_from=_parse_audit_datetime(
            date_from,
        ),
        date_to=_parse_audit_datetime(
            date_to,
            end_of_day=True,
        ),
    )
