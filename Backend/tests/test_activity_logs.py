from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta
from typing import Any

import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from Backend.sqlite.activity_models import ActivityLogModel
from app.firebase_auth import auth
from app.main import app
from Backend.sqlite.database import Base, get_db
from services.audit.activity_log_service import (
    CHAT_MESSAGE,
    DOCUMENT_DELETE,
    DOCUMENT_UPLOAD,
    LEAVE_ACCEPTED,
    LEAVE_CREATED,
    LEAVE_REJECTED,
    get_activity_summary,
    log_activity,
)


EMPLOYEE_USER = {
    "uid": "employee-activity",
    "email": "employee@example.com",
    "role": "employee",
}

MANAGER_USER = {
    "uid": "manager-activity",
    "email": "manager@example.com",
    "role": "manager",
}

ADMIN_USER = {
    "uid": "admin-activity",
    "email": "admin@example.com",
    "role": "admin",
}

TOKEN_USERS = {
    "employee-token": EMPLOYEE_USER,
    "manager-token": MANAGER_USER,
    "admin-token": ADMIN_USER,
}


def auth_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
    }


def seed_client_log(
    *,
    user_uid: str,
    email: str,
    role: str,
    action: str,
    resource: str,
    created_at: datetime,
    details: dict[str, Any] | None = None,
) -> None:
    db_override = app.dependency_overrides[get_db]
    db_iterator = db_override()
    db = next(db_iterator)

    try:
        log = log_activity(
            db,
            user_uid=user_uid,
            email=email,
            role=role,
            action=action,
            resource=resource,
            details=details or {},
        )
        log.created_at = created_at
        db.commit()
    finally:
        try:
            next(db_iterator)
        except StopIteration:
            pass


@pytest.fixture
def db_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def activity_client(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    def fake_verify_id_token(token: str) -> dict[str, str]:
        if token not in TOKEN_USERS:
            raise ValueError("Invalid test token")

        return TOKEN_USERS[token]

    monkeypatch.setattr(
        auth,
        "verify_id_token",
        fake_verify_id_token,
    )

    engine = create_engine(
        "sqlite://",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Iterator[Any]:
        db = TestingSessionLocal()

        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)

    try:
        yield client
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("action", "resource", "details"),
    [
        (
            CHAT_MESSAGE,
            "chat",
            {
                "message_length": 12,
            },
        ),
        (
            DOCUMENT_UPLOAD,
            "documents",
            {
                "filename": "procedure.txt",
                "type": "txt",
                "chunks": 3,
            },
        ),
        (
            DOCUMENT_DELETE,
            "documents",
            {
                "filename": "procedure.txt",
                "chunks_deleted": 3,
            },
        ),
        (
            LEAVE_CREATED,
            "leave_request",
            {
                "demande_id": "REQ-001",
                "type_conge": "conge_annuel",
            },
        ),
        (
            LEAVE_ACCEPTED,
            "leave_request",
            {
                "demande_id": "REQ-001",
            },
        ),
        (
            LEAVE_REJECTED,
            "leave_request",
            {
                "demande_id": "REQ-002",
            },
        ),
    ],
)
def test_log_activity_creates_expected_actions(
    db_session: Session,
    action: str,
    resource: str,
    details: dict[str, Any],
) -> None:
    log = log_activity(
        db_session,
        user_uid="user-1",
        email="user@example.com",
        role="employee",
        action=action,
        resource=resource,
        details=details,
    )

    saved = (
        db_session.query(ActivityLogModel)
        .filter(ActivityLogModel.id == log.id)
        .one()
    )

    assert saved.user_uid == "user-1"
    assert saved.email == "user@example.com"
    assert saved.role == "employee"
    assert saved.action == action
    assert saved.resource == resource
    assert saved.details is not None


def test_activity_summary_aggregates_seven_days_with_empty_days(
    db_session: Session,
) -> None:
    now = datetime.utcnow()

    log_activity(
        db_session,
        user_uid="admin-1",
        email="admin@example.com",
        role="admin",
        action=CHAT_MESSAGE,
        resource="chat",
        details={
            "message_length": 4,
        },
    )
    log_activity(
        db_session,
        user_uid="admin-1",
        email="admin@example.com",
        role="admin",
        action=DOCUMENT_UPLOAD,
        resource="documents",
        details={
            "filename": "today.txt",
            "type": "txt",
            "chunks": 1,
        },
    )
    old_log = log_activity(
        db_session,
        user_uid="manager-1",
        email="manager@example.com",
        role="manager",
        action=LEAVE_ACCEPTED,
        resource="leave_request",
        details={
            "demande_id": "REQ-OLD",
        },
    )
    old_log.created_at = now - timedelta(days=2)
    db_session.commit()

    summary = get_activity_summary(
        db_session,
        days=7,
    )

    assert summary["days"] == 7
    assert len(summary["daily"]) == 7
    assert summary["totals"] == {
        "chat_messages": 1,
        "documents_uploaded": 1,
        "documents_deleted": 0,
        "leave_created": 0,
        "leave_accepted": 1,
        "leave_rejected": 0,
    }
    assert any(
        day["chat_messages"] == 0
        and day["documents"] == 0
        and day["leave_requests"] == 0
        and day["manager_actions"] == 0
        for day in summary["daily"]
    )
    assert summary["daily"][-1]["chat_messages"] == 1
    assert summary["daily"][-1]["documents"] == 1
    assert summary["daily"][-3]["manager_actions"] == 1


@pytest.mark.parametrize(
    ("token", "expected_status"),
    [
        ("employee-token", 403),
        ("manager-token", 403),
        ("admin-token", 200),
    ],
)
def test_admin_activity_endpoint_rbac(
    activity_client: TestClient,
    token: str,
    expected_status: int,
) -> None:
    response = activity_client.get(
        "/api/admin/activity",
        headers=auth_headers(token),
    )

    assert response.status_code == expected_status


def test_admin_activity_endpoint_without_auth_returns_401(
    activity_client: TestClient,
) -> None:
    response = activity_client.get(
        "/api/admin/activity",
    )

    assert response.status_code == 401


def test_admin_activity_endpoint_returns_real_aggregation(
    activity_client: TestClient,
) -> None:
    db_override = app.dependency_overrides[get_db]
    db_iterator = db_override()
    db = next(db_iterator)

    try:
        log_activity(
            db,
            user_uid="admin-activity",
            email="admin@example.com",
            role="admin",
            action=DOCUMENT_DELETE,
            resource="documents",
            details={
                "filename": "obsolete.txt",
                "chunks_deleted": 2,
            },
        )
    finally:
        try:
            next(db_iterator)
        except StopIteration:
            pass

    response = activity_client.get(
        "/api/admin/activity?days=7",
        headers=auth_headers("admin-token"),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["days"] == 7
    assert len(data["daily"]) == 7
    assert data["totals"]["documents_deleted"] == 1
    assert data["daily"][-1]["documents"] >= 1
    assert data["recent"][0]["action"] == DOCUMENT_DELETE
    assert data["recent"][0]["details"]["filename"] == "obsolete.txt"


@pytest.mark.parametrize(
    ("token", "expected_status"),
    [
        ("employee-token", 403),
        ("manager-token", 403),
        ("admin-token", 200),
    ],
)
def test_admin_audit_logs_endpoint_rbac(
    activity_client: TestClient,
    token: str,
    expected_status: int,
) -> None:
    response = activity_client.get(
        "/api/admin/audit-logs",
        headers=auth_headers(token),
    )

    assert response.status_code == expected_status


def test_admin_audit_logs_endpoint_without_auth_returns_401(
    activity_client: TestClient,
) -> None:
    response = activity_client.get(
        "/api/admin/audit-logs",
    )

    assert response.status_code == 401


def test_admin_audit_logs_are_sorted_by_created_at_desc(
    activity_client: TestClient,
) -> None:
    seed_client_log(
        user_uid="user-old",
        email="old@example.com",
        role="employee",
        action=CHAT_MESSAGE,
        resource="chat",
        created_at=datetime(2026, 8, 14, 10, 0, 0),
        details={"message_length": 10},
    )
    seed_client_log(
        user_uid="user-new",
        email="new@example.com",
        role="admin",
        action=DOCUMENT_UPLOAD,
        resource="documents",
        created_at=datetime(2026, 8, 15, 10, 0, 0),
        details={"filename": "new.txt"},
    )

    response = activity_client.get(
        "/api/admin/audit-logs",
        headers=auth_headers("admin-token"),
    )

    assert response.status_code == 200
    data = response.json()
    assert [
        item["email"]
        for item in data["items"]
    ] == [
        "new@example.com",
        "old@example.com",
    ]


def test_admin_audit_logs_pagination(
    activity_client: TestClient,
) -> None:
    for index in range(3):
        seed_client_log(
            user_uid=f"user-{index}",
            email=f"user-{index}@example.com",
            role="employee",
            action=CHAT_MESSAGE,
            resource="chat",
            created_at=datetime(2026, 8, 15, 8, index, 0),
            details={"message_length": index},
        )

    response = activity_client.get(
        "/api/admin/audit-logs?page=2&page_size=2",
        headers=auth_headers("admin-token"),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 2
    assert data["page_size"] == 2
    assert data["total"] == 3
    assert data["total_pages"] == 2
    assert len(data["items"]) == 1


@pytest.mark.parametrize(
    ("query", "expected_email"),
    [
        ("action=DOCUMENT_UPLOAD", "admin-filter@example.com"),
        ("role=manager", "manager-filter@example.com"),
        ("resource=leave_request", "manager-filter@example.com"),
        ("user=employee-filter", "employee-filter@example.com"),
        ("user=uid-admin-filter", "admin-filter@example.com"),
        (
            "date_from=2026-08-15&date_to=2026-08-15",
            "admin-filter@example.com",
        ),
    ],
)
def test_admin_audit_logs_filters(
    activity_client: TestClient,
    query: str,
    expected_email: str,
) -> None:
    seed_client_log(
        user_uid="uid-employee-filter",
        email="employee-filter@example.com",
        role="employee",
        action=CHAT_MESSAGE,
        resource="chat",
        created_at=datetime(2026, 8, 14, 9, 0, 0),
        details={"message_length": 8},
    )
    seed_client_log(
        user_uid="uid-manager-filter",
        email="manager-filter@example.com",
        role="manager",
        action=LEAVE_ACCEPTED,
        resource="leave_request",
        created_at=datetime(2026, 8, 13, 9, 0, 0),
        details={"demande_id": "REQ-FILTER"},
    )
    seed_client_log(
        user_uid="uid-admin-filter",
        email="admin-filter@example.com",
        role="admin",
        action=DOCUMENT_UPLOAD,
        resource="documents",
        created_at=datetime(2026, 8, 15, 9, 0, 0),
        details={"filename": "filter.txt"},
    )

    response = activity_client.get(
        f"/api/admin/audit-logs?{query}",
        headers=auth_headers("admin-token"),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["email"] == expected_email


def test_admin_audit_logs_empty_result(
    activity_client: TestClient,
) -> None:
    seed_client_log(
        user_uid="uid-empty",
        email="empty@example.com",
        role="employee",
        action=CHAT_MESSAGE,
        resource="chat",
        created_at=datetime(2026, 8, 15, 9, 0, 0),
        details={"message_length": 8},
    )

    response = activity_client.get(
        "/api/admin/audit-logs?action=DOCUMENT_DELETE",
        headers=auth_headers("admin-token"),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["total_pages"] == 0


def test_admin_audit_logs_serializes_and_redacts_details(
    activity_client: TestClient,
) -> None:
    seed_client_log(
        user_uid="uid-details",
        email="details@example.com",
        role="admin",
        action=DOCUMENT_UPLOAD,
        resource="documents",
        created_at=datetime(2026, 8, 15, 9, 0, 0),
        details={
            "filename": "safe.txt",
            "password": "secret-password",
            "nested": {
                "firebase_token": "secret-token",
                "count": 2,
            },
        },
    )

    response = activity_client.get(
        "/api/admin/audit-logs",
        headers=auth_headers("admin-token"),
    )

    assert response.status_code == 200
    details = response.json()["items"][0]["details"]
    assert details["filename"] == "safe.txt"
    assert details["password"] == "[redacted]"
    assert details["nested"]["firebase_token"] == "[redacted]"
    assert details["nested"]["count"] == 2
