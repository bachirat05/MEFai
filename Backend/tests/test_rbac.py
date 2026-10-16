from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.firebase_auth import auth
from app.main import app
from Backend.sqlite.database import Base, get_db
from Backend.sqlite.leave_models import LeaveRequestModel

from api.routes import chat as chat_routes
from api.routes import conges as conges_routes
from api.routes import documents as documents_routes
from api.routes import system as system_routes
from services.workflows import leave_submission_service


EMPLOYEE_USER = {
    "uid": "employee-1",
    "email": "employee@example.com",
    "role": "employee",
}

MANAGER_USER = {
    "uid": "manager-1",
    "email": "manager@example.com",
    "role": "manager",
}

ADMIN_USER = {
    "uid": "admin-1",
    "email": "admin@example.com",
    "role": "admin",
}

TOKEN_USERS = {
    "employee-token": EMPLOYEE_USER,
    "manager-token": MANAGER_USER,
    "admin-token": ADMIN_USER,
}


class FakeRAGService:
    is_initialized = True

    def __init__(self) -> None:
        self.ingested_batches: list[list[Any]] = []
        self.deleted_batches: list[list[Any]] = []

    def ingest_batch(self, ingestions: list[Any]) -> list[str]:
        self.ingested_batches.append(ingestions)
        return [
            f"chunk-{index}"
            for index, _ in enumerate(
                ingestions,
                start=1,
            )
        ]

    def delete_batch(self, ingestions: list[Any]) -> list[str]:
        self.deleted_batches.append(ingestions)
        return [
            f"chunk-{index}"
            for index, _ in enumerate(
                ingestions,
                start=1,
            )
        ]


class FakeN8nService:
    async def soumettre_demande_conge(
        self,
        demande: Any,
        manager_email: str,
    ) -> dict[str, str]:
        return {
            "demande_id": "REQ-RBAC-001",
        }

    async def notifier_statut_demande(
        self,
        email: str,
        demande_id: str,
        statut: str,
    ) -> dict[str, str]:
        return {
            "status": "ok",
        }


class FakeOllamaResponse:
    status_code = 200


class FakeAsyncClient:
    def __init__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        pass

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc: object,
        traceback: object,
    ) -> None:
        return None

    async def get(self, url: str) -> FakeOllamaResponse:
        return FakeOllamaResponse()


def auth_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
    }


def leave_payload() -> dict[str, str]:
    return {
        "employe_id": "EMP-RBAC",
        "date_debut": "2026-09-01",
        "date_fin": "2026-09-03",
        "type_conge": "conge_annuel",
        "motif": "Test RBAC",
    }


def patch_firebase_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_verify_id_token(token: str) -> dict[str, str]:
        if token not in TOKEN_USERS:
            raise ValueError("Invalid test token")

        return TOKEN_USERS[token]

    monkeypatch.setattr(
        auth,
        "verify_id_token",
        fake_verify_id_token,
    )


@pytest.fixture
def rbac_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    patch_firebase_tokens(monkeypatch)

    documents_dir = (
        tmp_path
        / "documents"
    )
    documents_dir.mkdir()

    monkeypatch.setattr(
        documents_routes,
        "DOCUMENTS_DIR",
        documents_dir,
    )
    monkeypatch.setattr(
        system_routes,
        "DOCUMENTS_DIR",
        documents_dir,
    )
    monkeypatch.setattr(
        system_routes.httpx,
        "AsyncClient",
        FakeAsyncClient,
    )
    monkeypatch.setattr(
        conges_routes,
        "n8n_service",
        FakeN8nService(),
    )
    monkeypatch.setattr(
        leave_submission_service,
        "resolve_manager_email",
        lambda: "manager@example.com",
    )

    async def fake_get_tools(
        stack: Any,
        authenticated_user: dict[str, Any] | None = None,
    ) -> list[Any]:
        return ["fake-tool"]

    async def fake_run_agent(
        message: str,
        tools: list[Any],
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        return {
            "answer": "Reponse de test RBAC.",
            "tools_used": ["search_documents"],
        }

    monkeypatch.setattr(
        chat_routes.mcp_client,
        "get_tools",
        fake_get_tools,
    )
    monkeypatch.setattr(
        chat_routes.chat_service,
        "run_agent",
        fake_run_agent,
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

    seed_db = TestingSessionLocal()
    seed_db.add(
        LeaveRequestModel(
            demande_id="REQ-MANAGER-001",
            user_uid="employee-1",
            employee_email="employee@example.com",
            employe_id="EMP-RBAC",
            type_conge="conge_annuel",
            date_debut=date(2026, 9, 1),
            date_fin=date(2026, 9, 3),
            motif="Test manager patch",
            statut="pending",
            message="En attente",
        )
    )
    seed_db.add(
        LeaveRequestModel(
            demande_id="REQ-MANAGER-002",
            user_uid="employee-1",
            employee_email="employee@example.com",
            employe_id="EMP-RBAC",
            type_conge="conge_annuel",
            date_debut=date(2026, 9, 4),
            date_fin=date(2026, 9, 5),
            motif="Test manager reject",
            statut="pending",
            message="En attente",
        )
    )
    seed_db.commit()
    seed_db.close()

    def override_get_db() -> Iterator[Any]:
        db = TestingSessionLocal()

        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.state.rag_service = FakeRAGService()

    client = TestClient(app)

    try:
        yield client
    finally:
        app.dependency_overrides.clear()
        app.state.rag_service = None


@pytest.mark.parametrize(
    ("method", "url", "kwargs"),
    [
        ("get", "/api/documents", {}),
        ("get", "/api/admin/system-status", {}),
        ("get", "/api/admin/activity", {}),
        ("get", "/api/admin/audit-logs", {}),
        ("get", "/api/manager/conges", {}),
        ("get", "/api/conges", {}),
        (
            "post",
            "/api/chat",
            {
                "json": {
                    "message": "Bonjour",
                    "history": [],
                },
            },
        ),
    ],
)
def test_protected_endpoints_without_auth_return_401(
    rbac_client: TestClient,
    method: str,
    url: str,
    kwargs: dict[str, Any],
) -> None:
    response = getattr(rbac_client, method)(
        url,
        **kwargs,
    )

    assert response.status_code == 401


def test_invalid_token_returns_401(rbac_client: TestClient) -> None:
    response = rbac_client.get(
        "/api/conges",
        headers=auth_headers("invalid-token"),
    )

    assert response.status_code == 401


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        (
            "employee-token",
            {
                "/api/conges": 200,
                "/api/chat": 200,
                "/api/documents": 403,
                "/api/admin/system-status": 403,
                "/api/admin/activity": 403,
                "/api/admin/audit-logs": 403,
                "/api/manager/conges": 403,
            },
        ),
        (
            "manager-token",
            {
                "/api/conges": 200,
                "/api/chat": 200,
                "/api/documents": 403,
                "/api/admin/system-status": 403,
                "/api/admin/activity": 403,
                "/api/admin/audit-logs": 403,
                "/api/manager/conges": 200,
            },
        ),
        (
            "admin-token",
            {
                "/api/conges": 200,
                "/api/chat": 200,
                "/api/documents": 200,
                "/api/admin/system-status": 200,
                "/api/admin/activity": 200,
                "/api/admin/audit-logs": 200,
                "/api/manager/conges": 403,
            },
        ),
    ],
)
def test_rbac_matrix_for_read_endpoints(
    rbac_client: TestClient,
    token: str,
    expected: dict[str, int],
) -> None:
    headers = auth_headers(token)

    chat_response = rbac_client.post(
        "/api/chat",
        headers=headers,
        json={
            "message": "Bonjour",
            "history": [],
        },
    )

    responses = {
        "/api/conges": rbac_client.get(
            "/api/conges",
            headers=headers,
        ),
        "/api/chat": chat_response,
        "/api/documents": rbac_client.get(
            "/api/documents",
            headers=headers,
        ),
        "/api/admin/system-status": rbac_client.get(
            "/api/admin/system-status",
            headers=headers,
        ),
        "/api/admin/activity": rbac_client.get(
            "/api/admin/activity",
            headers=headers,
        ),
        "/api/admin/audit-logs": rbac_client.get(
            "/api/admin/audit-logs",
            headers=headers,
        ),
        "/api/manager/conges": rbac_client.get(
            "/api/manager/conges",
            headers=headers,
        ),
    }

    assert {
        url: response.status_code
        for url, response in responses.items()
    } == expected


@pytest.mark.parametrize(
    ("token", "expected_status"),
    [
        ("employee-token", 403),
        ("manager-token", 200),
        ("admin-token", 403),
    ],
)
def test_manager_patch_allows_manager_only(
    rbac_client: TestClient,
    token: str,
    expected_status: int,
) -> None:
    response = rbac_client.patch(
        "/api/manager/conges/REQ-MANAGER-001",
        headers=auth_headers(token),
        json={
            "statut": "accepted",
        },
    )

    assert response.status_code == expected_status

    if token == "manager-token":
        assert response.json()["statut"] == "accepted"


def test_manager_patch_without_auth_returns_401(
    rbac_client: TestClient,
) -> None:
    response = rbac_client.patch(
        "/api/manager/conges/REQ-MANAGER-001",
        json={
            "statut": "accepted",
        },
    )

    assert response.status_code == 401


def test_manager_can_reject_leave_request(
    rbac_client: TestClient,
) -> None:
    response = rbac_client.patch(
        "/api/manager/conges/REQ-MANAGER-002",
        headers=auth_headers("manager-token"),
        json={
            "statut": "rejected",
        },
    )

    assert response.status_code == 200
    assert response.json()["statut"] == "rejected"


@pytest.mark.parametrize(
    "token",
    [
        "employee-token",
        "manager-token",
        "admin-token",
    ],
)
def test_authenticated_users_can_access_employee_leave_endpoints(
    rbac_client: TestClient,
    token: str,
) -> None:
    headers = auth_headers(token)

    get_response = rbac_client.get(
        "/api/conges",
        headers=headers,
    )
    post_response = rbac_client.post(
        "/api/conges",
        headers=headers,
        json=leave_payload(),
    )

    assert get_response.status_code == 200
    assert post_response.status_code == 200


@pytest.mark.parametrize(
    ("token", "expected_status"),
    [
        ("employee-token", 403),
        ("manager-token", 403),
        ("admin-token", 200),
    ],
)
def test_document_upload_is_admin_only(
    rbac_client: TestClient,
    token: str,
    expected_status: int,
) -> None:
    response = rbac_client.post(
        "/api/documents/upload",
        headers=auth_headers(token),
        files={
            "file": (
                "rbac_upload.txt",
                b"Document RBAC upload.",
                "text/plain",
            ),
        },
    )

    assert response.status_code == expected_status


@pytest.mark.parametrize(
    ("token", "expected_status"),
    [
        ("employee-token", 403),
        ("manager-token", 403),
        ("admin-token", 200),
    ],
)
def test_document_delete_is_admin_only(
    rbac_client: TestClient,
    token: str,
    expected_status: int,
) -> None:
    file_path = (
        documents_routes.DOCUMENTS_DIR
        / f"delete_{token}.txt"
    )
    file_path.write_text(
        "Document RBAC delete.",
        encoding="utf-8",
    )

    response = rbac_client.delete(
        f"/api/documents/{file_path.name}",
        headers=auth_headers(token),
    )

    assert response.status_code == expected_status


@pytest.mark.parametrize(
    "url",
    [
        "/api/documents/..%2Fsecret.txt",
        "/api/documents/%2E%2E%5Csecret.txt",
    ],
)
def test_document_delete_rejects_path_traversal(
    rbac_client: TestClient,
    url: str,
) -> None:
    response = rbac_client.delete(
        url,
        headers=auth_headers("admin-token"),
    )

    assert response.status_code in {400, 404}


def test_document_delete_rejects_invalid_extension(
    rbac_client: TestClient,
) -> None:
    response = rbac_client.delete(
        "/api/documents/malware.exe",
        headers=auth_headers("admin-token"),
    )

    assert response.status_code == 400


def test_document_delete_missing_file_returns_404(
    rbac_client: TestClient,
) -> None:
    response = rbac_client.delete(
        "/api/documents/missing.txt",
        headers=auth_headers("admin-token"),
    )

    assert response.status_code == 404
