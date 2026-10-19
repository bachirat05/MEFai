from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api.routes import conges as conges_routes
from app import firebase_auth
from app.firebase_auth import ManagerResolutionError
from app.main import app
from Backend.sqlite.database import Base, get_db

from Backend.sqlite.leave_models import LeaveRequestModel

from schemas.workflow import DemandeConge, TypeConge
from services.workflows import leave_submission_service
from services.workflows.leave_submission_service import (
    NoManagerAvailableError,
    submit_leave_request,
)
from services.workflows.n8n_service import N8nService


EMPLOYEE_USER = {
    "uid": "employee-1",
    "email": "employee@example.com",
    "role": "employee",
}


class FakeFirebaseUser:
    def __init__(
        self,
        *,
        email: str | None,
        custom_claims: dict[str, Any] | None,
    ) -> None:
        self.email = email
        self.custom_claims = custom_claims


class FakeListUsersResult:
    def __init__(
        self,
        users: list[FakeFirebaseUser],
    ) -> None:
        self._users = users

    def iterate_all(self) -> list[FakeFirebaseUser]:
        return self._users


class RecordingN8nService:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def soumettre_demande_conge(
        self,
        demande: DemandeConge,
        manager_email: str,
    ) -> dict[str, str]:
        self.calls.append(
            {
                "demande": demande,
                "manager_email": manager_email,
            }
        )
        return {
            "demande_id": "REQ-TEST-001",
        }


def demande() -> DemandeConge:
    return DemandeConge(
        employe_id="EMP-001",
        date_debut="2026-08-20",
        date_fin="2026-08-24",
        type_conge=TypeConge.CONGE_ANNUEL,
        motif="Congé annuel",
    )


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


def patch_firebase_users(
    monkeypatch: pytest.MonkeyPatch,
    users: list[FakeFirebaseUser],
) -> None:
    monkeypatch.setattr(
        firebase_auth.auth,
        "list_users",
        lambda: FakeListUsersResult(users),
    )


def test_resolve_manager_email_ignores_other_roles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_firebase_users(
        monkeypatch,
        [
            FakeFirebaseUser(
                email="employee@example.com",
                custom_claims={
                    "role": "employee",
                },
            ),
            FakeFirebaseUser(
                email="manager@example.com",
                custom_claims={
                    "role": "manager",
                },
            ),
        ],
    )

    assert firebase_auth.resolve_manager_email() == "manager@example.com"


def test_resolve_manager_email_ignores_manager_without_email(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_firebase_users(
        monkeypatch,
        [
            FakeFirebaseUser(
                email="",
                custom_claims={
                    "role": "manager",
                },
            ),
            FakeFirebaseUser(
                email="valid.manager@example.com",
                custom_claims={
                    "role": "manager",
                },
            ),
        ],
    )

    assert (
        firebase_auth.resolve_manager_email()
        == "valid.manager@example.com"
    )


def test_resolve_manager_email_uses_deterministic_email_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_firebase_users(
        monkeypatch,
        [
            FakeFirebaseUser(
                email="z.manager@example.com",
                custom_claims={
                    "role": "manager",
                },
            ),
            FakeFirebaseUser(
                email="a.manager@example.com",
                custom_claims={
                    "role": "manager",
                },
            ),
        ],
    )

    assert firebase_auth.resolve_manager_email() == "a.manager@example.com"


@pytest.mark.asyncio
async def test_submit_leave_request_sends_resolved_manager_email_to_n8n(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
) -> None:
    monkeypatch.setattr(
        leave_submission_service,
        "resolve_manager_email",
        lambda: "manager@example.com",
    )
    n8n_service = RecordingN8nService()

    response = await submit_leave_request(
        demande=demande(),
        user=EMPLOYEE_USER,
        db=db_session,
        n8n_service=n8n_service,  # type: ignore[arg-type]
    )

    assert response.demande_id == "REQ-TEST-001"
    assert response.statut == "pending"
    assert n8n_service.calls[0]["manager_email"] == "manager@example.com"


@pytest.mark.asyncio
async def test_submit_leave_request_without_manager_does_not_call_n8n(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
) -> None:
    def raise_no_manager() -> str:
        raise ManagerResolutionError(
            "Aucun manager Firebase valide trouvé."
        )

    monkeypatch.setattr(
        leave_submission_service,
        "resolve_manager_email",
        raise_no_manager,
    )
    n8n_service = RecordingN8nService()

    with pytest.raises(NoManagerAvailableError):
        await submit_leave_request(
            demande=demande(),
            user=EMPLOYEE_USER,
            db=db_session,
            n8n_service=n8n_service,  # type: ignore[arg-type]
        )

    assert n8n_service.calls == []


def test_post_conges_without_manager_returns_controlled_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_verify_id_token(token: str) -> dict[str, str]:
        return EMPLOYEE_USER

    def raise_no_manager() -> str:
        raise ManagerResolutionError(
            "Aucun manager Firebase valide trouvé."
        )

    n8n_service = RecordingN8nService()

    monkeypatch.setattr(
        firebase_auth.auth,
        "verify_id_token",
        fake_verify_id_token,
    )
    monkeypatch.setattr(
        leave_submission_service,
        "resolve_manager_email",
        raise_no_manager,
    )
    monkeypatch.setattr(
        conges_routes,
        "n8n_service",
        n8n_service,
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

    try:
        client = TestClient(app)
        response = client.post(
            "/api/conges",
            headers={
                "Authorization": "Bearer employee-token",
            },
            json=demande().model_dump(mode="json"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "Aucun manager valide n'est configuré pour recevoir la demande."
    )
    assert n8n_service.calls == []


def test_manager_email_from_frontend_payload_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        firebase_auth.auth,
        "verify_id_token",
        lambda token: EMPLOYEE_USER,
    )

    client = TestClient(app)
    payload = demande().model_dump(mode="json")
    payload["manager_email"] = "attacker@example.com"

    response = client.post(
        "/api/conges",
        headers={
            "Authorization": "Bearer employee-token",
        },
        json=payload,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_n8n_service_adds_manager_email_to_webhook_payload() -> None:
    service = N8nService(
        webhook_url="http://localhost:5678/webhook/test",
        secret_token="test-secret",
        timeout_seconds=10.0,
    )
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.headers = {
        "content-type": "application/json",
    }
    mock_response.json = MagicMock(
        return_value={
            "demande_id": "REQ-001",
        }
    )
    mock_response.raise_for_status = MagicMock()

    mock_post = AsyncMock(
        return_value=mock_response
    )

    with patch(
        "httpx.AsyncClient.post",
        mock_post,
    ):
        await service.soumettre_demande_conge(
            demande(),
            manager_email="manager@example.com",
        )

    payload = mock_post.call_args.kwargs["json"]
    assert payload["manager_email"] == "manager@example.com"
    assert "manager_email" not in DemandeConge.model_fields
