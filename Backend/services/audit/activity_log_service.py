from __future__ import annotations

import json
import logging

from collections import Counter
from datetime import datetime, time, timedelta
from typing import Any

from sqlalchemy import Engine, func, or_, text
from sqlalchemy.orm import Session

from Backend.sqlite.activity_models import ActivityLogModel


logger = logging.getLogger(__name__)


CHAT_MESSAGE = "CHAT_MESSAGE"
DOCUMENT_UPLOAD = "DOCUMENT_UPLOAD"
DOCUMENT_DELETE = "DOCUMENT_DELETE"
LEAVE_CREATED = "LEAVE_CREATED"
LEAVE_ACCEPTED = "LEAVE_ACCEPTED"
LEAVE_REJECTED = "LEAVE_REJECTED"

TOTAL_KEYS = {
    CHAT_MESSAGE: "chat_messages",
    DOCUMENT_UPLOAD: "documents_uploaded",
    DOCUMENT_DELETE: "documents_deleted",
    LEAVE_CREATED: "leave_created",
    LEAVE_ACCEPTED: "leave_accepted",
    LEAVE_REJECTED: "leave_rejected",
}

SENSITIVE_DETAIL_KEYS = {
    "authorization",
    "authorization_header",
    "firebase_token",
    "id_token",
    "n8n_secret",
    "password",
    "prompt",
    "secret",
    "system_prompt",
    "token",
}


def _encode_details(
    details: dict[str, Any] | str | None,
) -> str | None:
    if details is None:
        return None

    if isinstance(details, str):
        return details

    return json.dumps(
        details,
        ensure_ascii=False,
        default=str,
    )


def _sanitize_details_value(
    key: str,
    value: Any,
) -> Any:
    normalized_key = key.lower()

    if any(
        sensitive_key in normalized_key
        for sensitive_key in SENSITIVE_DETAIL_KEYS
    ):
        return "[redacted]"

    if isinstance(value, dict):
        return {
            child_key: _sanitize_details_value(
                child_key,
                child_value,
            )
            for child_key, child_value in value.items()
        }

    if isinstance(value, list):
        return [
            _sanitize_details_value(
                key,
                item,
            )
            for item in value
        ]

    return value


def _sanitize_details(
    details: dict[str, Any] | str | None,
) -> dict[str, Any] | str | None:
    if not isinstance(details, dict):
        return details

    return {
        key: _sanitize_details_value(
            key,
            value,
        )
        for key, value in details.items()
    }


def _decode_details(
    details: str | None,
) -> dict[str, Any] | str | None:
    if details is None:
        return None

    try:
        decoded: Any = json.loads(details)
    except json.JSONDecodeError:
        return details

    if isinstance(decoded, dict):
        return _sanitize_details(decoded)

    return details


def log_activity(
    db: Session,
    *,
    user_uid: str,
    email: str | None,
    role: str | None,
    action: str,
    resource: str,
    details: dict[str, Any] | str | None = None,
) -> ActivityLogModel:
    log = ActivityLogModel(
        user_uid=user_uid,
        email=email,
        role=role,
        action=action,
        resource=resource,
        details=_encode_details(details),
    )

    db.add(log)
    db.commit()
    db.refresh(log)

    return log


def safe_log_activity(
    db: Session,
    *,
    user: dict[str, Any],
    action: str,
    resource: str,
    details: dict[str, Any] | str | None = None,
) -> ActivityLogModel | None:
    try:
        return log_activity(
            db,
            user_uid=str(user.get("uid", "")),
            email=user.get("email"),
            role=user.get("role"),
            action=action,
            resource=resource,
            details=details,
        )
    except Exception as exc:
        db.rollback()
        logger.exception(
            "Activity log failed for action=%s resource=%s: %s",
            action,
            resource,
            exc,
        )
        return None


def get_activity_summary(
    db: Session,
    *,
    days: int = 7,
    recent_limit: int = 10,
) -> dict[str, Any]:
    safe_days = max(
        1,
        min(days, 90),
    )

    today = datetime.utcnow().date()
    start_date = today - timedelta(days=safe_days - 1)
    start_at = datetime.combine(
        start_date,
        time.min,
    )

    logs = (
        db.query(ActivityLogModel)
        .filter(ActivityLogModel.created_at >= start_at)
        .order_by(ActivityLogModel.created_at.asc())
        .all()
    )

    totals = {
        "chat_messages": 0,
        "documents_uploaded": 0,
        "documents_deleted": 0,
        "leave_created": 0,
        "leave_accepted": 0,
        "leave_rejected": 0,
    }

    daily_counts: dict[str, Counter[str]] = {
        (
            start_date
            + timedelta(days=index)
        ).isoformat(): Counter()
        for index in range(safe_days)
    }

    for log in logs:
        total_key = TOTAL_KEYS.get(log.action)
        if total_key is not None:
            totals[total_key] += 1

        day_key = log.created_at.date().isoformat()
        if day_key not in daily_counts:
            continue

        if log.action == CHAT_MESSAGE:
            daily_counts[day_key]["chat_messages"] += 1
        elif log.action in {
            DOCUMENT_UPLOAD,
            DOCUMENT_DELETE,
        }:
            daily_counts[day_key]["documents"] += 1
        elif log.action == LEAVE_CREATED:
            daily_counts[day_key]["leave_requests"] += 1
        elif log.action in {
            LEAVE_ACCEPTED,
            LEAVE_REJECTED,
        }:
            daily_counts[day_key]["manager_actions"] += 1

    daily = [
        {
            "date": day,
            "chat_messages": daily_counts[day]["chat_messages"],
            "documents": daily_counts[day]["documents"],
            "leave_requests": daily_counts[day]["leave_requests"],
            "manager_actions": daily_counts[day]["manager_actions"],
        }
        for day in daily_counts
    ]

    recent_logs = (
        db.query(ActivityLogModel)
        .filter(ActivityLogModel.action != CHAT_MESSAGE)
        .order_by(ActivityLogModel.created_at.desc())
        .limit(recent_limit)
        .all()
    )

    recent = [
        {
            "action": log.action,
            "resource": log.resource,
            "email": log.email,
            "role": log.role,
            "created_at": log.created_at.isoformat(),
            "details": _decode_details(log.details),
        }
        for log in recent_logs
    ]

    return {
        "days": safe_days,
        "totals": totals,
        "daily": daily,
        "recent": recent,
    }


def get_audit_logs(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    action: str | None = None,
    role: str | None = None,
    resource: str | None = None,
    user: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict[str, Any]:
    safe_page = max(page, 1)
    safe_page_size = max(
        1,
        min(page_size, 100),
    )

    query = db.query(ActivityLogModel)

    if action:
        query = query.filter(
            ActivityLogModel.action == action
        )

    if role:
        query = query.filter(
            ActivityLogModel.role == role
        )

    if resource:
        query = query.filter(
            ActivityLogModel.resource == resource
        )

    if user:
        search = f"%{user.strip()}%"
        query = query.filter(
            or_(
                ActivityLogModel.email.ilike(search),
                ActivityLogModel.user_uid.ilike(search),
            )
        )

    if date_from:
        query = query.filter(
            ActivityLogModel.created_at >= date_from
        )

    if date_to:
        query = query.filter(
            ActivityLogModel.created_at <= date_to
        )

    total = (
        query.with_entities(
            func.count(ActivityLogModel.id)
        )
        .scalar()
        or 0
    )

    total_pages = (
        (total + safe_page_size - 1)
        // safe_page_size
        if total > 0
        else 0
    )

    logs = (
        query.order_by(
            ActivityLogModel.created_at.desc(),
            ActivityLogModel.id.desc(),
        )
        .offset(
            (safe_page - 1)
            * safe_page_size
        )
        .limit(safe_page_size)
        .all()
    )

    return {
        "items": [
            {
                "id": log.id,
                "user_uid": log.user_uid,
                "email": log.email,
                "role": log.role,
                "action": log.action,
                "resource": log.resource,
                "details": _decode_details(log.details),
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
        "page": safe_page,
        "page_size": safe_page_size,
        "total": total,
        "total_pages": total_pages,
    }


def ensure_activity_log_indexes(
    engine: Engine,
) -> None:
    index_statements = [
        (
            "CREATE INDEX IF NOT EXISTS "
            "ix_activity_logs_created_at "
            "ON activity_logs (created_at)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS "
            "ix_activity_logs_action "
            "ON activity_logs (action)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS "
            "ix_activity_logs_role "
            "ON activity_logs (role)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS "
            "ix_activity_logs_resource "
            "ON activity_logs (resource)"
        ),
    ]

    with engine.begin() as connection:
        for statement in index_statements:
            connection.execute(
                text(statement)
            )
