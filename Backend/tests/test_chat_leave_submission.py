from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.tools import StructuredTool
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.routes import conges as conges_routes
from app import firebase_auth
from app import main as app_main
from app.main import app
from Backend.sqlite.database import Base, get_db
from Backend.sqlite.leave_models import LeaveRequestModel
from services.chat import chat_service as chat_service_module
from services.chat.chat_service import ChatService
from services.workflows import leave_submission_service
from services.workflows.n8n_service import N8nServiceError


EMPLOYEE_USER = {
    "uid": "employee-chat",
    "email": "employee.chat@example.com",
    "role": "employee",
}

MANAGER_USER = {
    "uid": "manager-chat",
    "email": "manager.chat@example.com",
    "role": "manager",
}


class RecordingN8nService:
    def __init__(
        self,
        *,
        fail: bool = False,
    ) -> None:
        self.fail = fail
        self.calls: list[dict[str, Any]] = []

    async def soumettre_demande_conge(
        self,
        demande: Any,
        manager_email: str,
    ) -> dict[str, str]:
        if self.fail:
            raise N8nServiceError("n8n down")

        self.calls.append(
            {
                "demande": demande,
                "manager_email": manager_email,
            }
        )
        return {
            "demande_id": "REQ-CHAT-001",
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


@pytest.fixture
def app_db(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[sessionmaker]:
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
    monkeypatch.setattr(
        app_main,
        "SessionLocal",
        TestingSessionLocal,
    )

    try:
        yield TestingSessionLocal
    finally:
        app.dependency_overrides.clear()


async def fake_submit_tool(**kwargs: Any) -> str:
    return (
        "Votre demande REQ-FAKE a bien été créée et transmise au manager. "
        "Statut: pending. Période: 2026-08-20 au 2026-08-24. "
        "Type de congé: conge_annuel."
    )


def build_submit_tool(
    calls: list[dict[str, Any]],
) -> StructuredTool:
    async def submit(**kwargs: Any) -> str:
        calls.append(kwargs)
        return await fake_submit_tool(**kwargs)

    return StructuredTool.from_function(
        coroutine=submit,
        name="soumettre_demande_conge",
        description="Soumet une demande de congé.",
    )


@pytest.mark.asyncio
async def test_chat_complete_leave_intent_calls_submit_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []
    tool = build_submit_tool(calls)

    class FakeAgent:
        async def ainvoke(
            self,
            payload: dict[str, Any],
            config: dict[str, Any],
        ) -> dict[str, Any]:
            result = await tool.ainvoke(
                {
                    "employe_id": "EMP-001",
                    "date_debut": "2026-08-20",
                    "date_fin": "2026-08-24",
                    "type_conge": "conge_annuel",
                    "motif": "Congé annuel",
                }
            )

            class Message:
                content = result
                tool_calls = [
                    {
                        "name": "soumettre_demande_conge",
                    }
                ]

            return {
                "messages": [
                    Message(),
                ]
            }

    monkeypatch.setattr(
        ChatService,
        "_get_model",
        lambda self: object(),
    )
    monkeypatch.setattr(
        chat_service_module,
        "create_react_agent",
        lambda model, tools: FakeAgent(),
    )

    result = await ChatService().run_agent(
        message="Je veux demander un congé du 20 au 24 août.",
        tools=[
            tool,
        ],
    )

    assert calls
    assert result["tools_used"] == [
        "soumettre_demande_conge",
    ]


@pytest.mark.asyncio
async def test_chat_missing_fields_does_not_submit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []
    tool = build_submit_tool(calls)

    class FakeAgent:
        async def ainvoke(
            self,
            payload: dict[str, Any],
            config: dict[str, Any],
        ) -> dict[str, Any]:
            class Message:
                content = (
                    "Quel type de congé souhaitez-vous demander "
                    "et quel est le motif ?"
                )
                tool_calls: list[dict[str, str]] = []

            return {
                "messages": [
                    Message(),
                ]
            }

    monkeypatch.setattr(
        ChatService,
        "_get_model",
        lambda self: object(),
    )
    monkeypatch.setattr(
        chat_service_module,
        "create_react_agent",
        lambda model, tools: FakeAgent(),
    )

    result = await ChatService().run_agent(
        message="Je veux prendre un congé du 20 au 24 août.",
        tools=[
            tool,
        ],
    )

    assert calls == []
    assert result["tools_used"] == []
    assert "type de congé" in result["answer"]


@pytest.mark.asyncio
async def test_mcp_leave_tool_resolves_manager_and_persists(
    monkeypatch: pytest.MonkeyPatch,
    app_db: sessionmaker,
) -> None:
    n8n_service = RecordingN8nService()
    monkeypatch.setattr(
        leave_submission_service,
        "resolve_manager_email",
        lambda: "manager.chat@example.com",
    )
    monkeypatch.setattr(
        app_main,
        "n8n_service",
        n8n_service,
    )

    result = await app_main.soumettre_demande_conge(
        employe_id="EMP-CHAT",
        date_debut="2026-09-03",
        date_fin="2026-09-05",
        type_conge="conge_annuel",
        motif="Congé annuel",
        user_uid=EMPLOYEE_USER["uid"],
        employee_email=EMPLOYEE_USER["email"],
        user_role=EMPLOYEE_USER["role"],
    )

    db = app_db()
    try:
        saved = (
            db.query(LeaveRequestModel)
            .filter(
                LeaveRequestModel.demande_id == "REQ-CHAT-001"
            )
            .one()
        )
    finally:
        db.close()

    assert "REQ-CHAT-001" in result
    assert n8n_service.calls[0]["manager_email"] == "manager.chat@example.com"
    assert saved.statut == "pending"
    assert saved.user_uid == EMPLOYEE_USER["uid"]


def test_mcp_created_leave_appears_in_employee_and_manager_views(
    monkeypatch: pytest.MonkeyPatch,
    app_db: sessionmaker,
) -> None:
    def fake_verify_id_token(token: str) -> dict[str, str]:
        if token == "employee-token":
            return EMPLOYEE_USER
        return MANAGER_USER

    monkeypatch.setattr(
        firebase_auth.auth,
        "verify_id_token",
        fake_verify_id_token,
    )
    monkeypatch.setattr(
        conges_routes,
        "n8n_service",
        RecordingN8nService(),
    )

    db = app_db()
    try:
        db.add(
            LeaveRequestModel(
                demande_id="REQ-CHAT-002",
                user_uid=EMPLOYEE_USER["uid"],
                employee_email=EMPLOYEE_USER["email"],
                employe_id="EMP-CHAT",
                type_conge="conge_annuel",
                date_debut=date(2026, 9, 3),
                date_fin=date(2026, 9, 5),
                motif="Congé annuel",
                statut="pending",
                message="En attente",
            )
        )
        db.commit()
    finally:
        db.close()

    client = TestClient(app)
    employee_response = client.get(
        "/api/conges",
        headers={
            "Authorization": "Bearer employee-token",
        },
    )
    manager_response = client.get(
        "/api/manager/conges",
        headers={
            "Authorization": "Bearer manager-token",
        },
    )
    patch_response = client.patch(
        "/api/manager/conges/REQ-CHAT-002",
        headers={
            "Authorization": "Bearer manager-token",
        },
        json={
            "statut": "accepted",
        },
    )

    assert employee_response.status_code == 200
    assert manager_response.status_code == 200
    assert patch_response.status_code == 200
    assert employee_response.json()[0]["demande_id"] == "REQ-CHAT-002"
    assert manager_response.json()[0]["demande_id"] == "REQ-CHAT-002"
    assert patch_response.json()["statut"] == "accepted"


@pytest.mark.asyncio
async def test_mcp_leave_tool_n8n_error_returns_no_false_success(
    monkeypatch: pytest.MonkeyPatch,
    app_db: sessionmaker,
) -> None:
    monkeypatch.setattr(
        leave_submission_service,
        "resolve_manager_email",
        lambda: "manager.chat@example.com",
    )
    monkeypatch.setattr(
        app_main,
        "n8n_service",
        RecordingN8nService(fail=True),
    )

    result = await app_main.soumettre_demande_conge(
        employe_id="EMP-CHAT",
        date_debut="2026-09-03",
        date_fin="2026-09-05",
        type_conge="conge_annuel",
        motif="Congé annuel",
        user_uid=EMPLOYEE_USER["uid"],
        employee_email=EMPLOYEE_USER["email"],
        user_role=EMPLOYEE_USER["role"],
    )

    db = app_db()
    try:
        count = db.query(LeaveRequestModel).count()
    finally:
        db.close()

    assert result.startswith("Error: n8n workflow failed")
    assert count == 0
