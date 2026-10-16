from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.routes import chat as chat_routes
from app.firebase_auth import auth
from app.main import app
from Backend.sqlite.chat_models import ChatMessageModel, ConversationModel
from Backend.sqlite.database import Base, get_db


EMPLOYEE_USER = {
    "uid": "employee-chat-persist",
    "email": "employee@example.com",
    "role": "employee",
}

MANAGER_USER = {
    "uid": "manager-chat-persist",
    "email": "manager@example.com",
    "role": "manager",
}

ADMIN_USER = {
    "uid": "admin-chat-persist",
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


@pytest.fixture
def chat_client(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[TestClient, sessionmaker]]:
    def fake_verify_id_token(token: str) -> dict[str, str]:
        if token not in TOKEN_USERS:
            raise ValueError("Invalid token")

        return TOKEN_USERS[token]

    monkeypatch.setattr(
        auth,
        "verify_id_token",
        fake_verify_id_token,
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
            "answer": f"Réponse à: {message}",
            "tools_used": [],
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

    def override_get_db() -> Iterator[Any]:
        db = TestingSessionLocal()

        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)

    try:
        yield client, TestingSessionLocal
    finally:
        app.dependency_overrides.clear()


def seed_conversation(
    SessionLocal: sessionmaker,
    *,
    user_uid: str,
    title: str,
    updated_at: datetime | None = None,
) -> int:
    db = SessionLocal()

    try:
        conversation = ConversationModel(
            user_uid=user_uid,
            title=title,
        )
        if updated_at is not None:
            conversation.updated_at = updated_at

        db.add(conversation)
        db.flush()
        db.add_all(
            [
                ChatMessageModel(
                    conversation_id=conversation.id,
                    role="user",
                    content=f"Question {title}",
                ),
                ChatMessageModel(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=f"Réponse {title}",
                ),
            ]
        )
        db.commit()
        return conversation.id
    finally:
        db.close()


def test_conversation_created_for_employee(
    chat_client: tuple[TestClient, sessionmaker],
) -> None:
    client, SessionLocal = chat_client

    response = client.post(
        "/api/conversations",
        headers=auth_headers("employee-token"),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Nouvelle conversation"

    db = SessionLocal()
    try:
        saved = db.query(ConversationModel).one()
        assert saved.user_uid == EMPLOYEE_USER["uid"]
    finally:
        db.close()


def test_employee_sees_only_own_conversations(
    chat_client: tuple[TestClient, sessionmaker],
) -> None:
    client, SessionLocal = chat_client
    employee_first_id = seed_conversation(
        SessionLocal,
        user_uid=EMPLOYEE_USER["uid"],
        title="Employee conversation 1",
    )
    employee_second_id = seed_conversation(
        SessionLocal,
        user_uid=EMPLOYEE_USER["uid"],
        title="Employee conversation 2",
    )
    manager_id = seed_conversation(
        SessionLocal,
        user_uid=MANAGER_USER["uid"],
        title="Manager conversation",
    )

    response = client.get(
        "/api/conversations",
        headers=auth_headers("employee-token"),
    )

    assert response.status_code == 200
    employee_data = response.json()
    assert {
        item["id"]
        for item in employee_data
    } == {
        employee_first_id,
        employee_second_id,
    }
    assert all(
        item["title"].startswith("Employee conversation")
        for item in employee_data
    )

    manager_response = client.get(
        "/api/conversations",
        headers=auth_headers("manager-token"),
    )

    assert manager_response.status_code == 200
    assert manager_response.json() == [
        {
            "id": manager_id,
            "title": "Manager conversation",
            "created_at": manager_response.json()[0]["created_at"],
            "updated_at": manager_response.json()[0]["updated_at"],
            "message_count": 2,
        }
    ]


def test_manager_and_admin_do_not_see_employee_conversations(
    chat_client: tuple[TestClient, sessionmaker],
) -> None:
    client, SessionLocal = chat_client
    seed_conversation(
        SessionLocal,
        user_uid=EMPLOYEE_USER["uid"],
        title="Employee private",
    )

    manager_response = client.get(
        "/api/conversations",
        headers=auth_headers("manager-token"),
    )
    admin_response = client.get(
        "/api/conversations",
        headers=auth_headers("admin-token"),
    )

    assert manager_response.status_code == 200
    assert admin_response.status_code == 200
    assert manager_response.json() == []
    assert admin_response.json() == []


def test_get_conversation_by_id_returns_owner_history(
    chat_client: tuple[TestClient, sessionmaker],
) -> None:
    client, SessionLocal = chat_client
    conversation_id = seed_conversation(
        SessionLocal,
        user_uid=EMPLOYEE_USER["uid"],
        title="Questions RH",
    )

    response = client.get(
        f"/api/conversations/{conversation_id}",
        headers=auth_headers("employee-token"),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == conversation_id
    assert data["title"] == "Questions RH"
    assert [
        message["role"]
        for message in data["messages"]
    ] == [
        "user",
        "assistant",
    ]


def test_direct_access_to_other_user_conversation_is_refused(
    chat_client: tuple[TestClient, sessionmaker],
) -> None:
    client, SessionLocal = chat_client
    conversation_id = seed_conversation(
        SessionLocal,
        user_uid=EMPLOYEE_USER["uid"],
        title="Employee private",
    )

    response = client.get(
        f"/api/conversations/{conversation_id}",
        headers=auth_headers("manager-token"),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation introuvable"


def test_get_unknown_conversation_returns_404(
    chat_client: tuple[TestClient, sessionmaker],
) -> None:
    client, _ = chat_client

    response = client.get(
        "/api/conversations/999999",
        headers=auth_headers("employee-token"),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation introuvable"


def test_delete_owned_conversation_removes_messages_and_list_entry(
    chat_client: tuple[TestClient, sessionmaker],
) -> None:
    client, SessionLocal = chat_client
    conversation_id = seed_conversation(
        SessionLocal,
        user_uid=EMPLOYEE_USER["uid"],
        title="A supprimer",
    )

    response = client.delete(
        f"/api/conversations/{conversation_id}",
        headers=auth_headers("employee-token"),
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Conversation supprimée",
        "conversation_id": conversation_id,
    }

    db = SessionLocal()
    try:
        assert (
            db.query(ConversationModel)
            .filter(ConversationModel.id == conversation_id)
            .first()
            is None
        )
        assert (
            db.query(ChatMessageModel)
            .filter(ChatMessageModel.conversation_id == conversation_id)
            .count()
            == 0
        )
    finally:
        db.close()

    list_response = client.get(
        "/api/conversations",
        headers=auth_headers("employee-token"),
    )

    assert list_response.status_code == 200
    assert all(
        item["id"] != conversation_id
        for item in list_response.json()
    )


def test_delete_other_user_conversation_is_refused(
    chat_client: tuple[TestClient, sessionmaker],
) -> None:
    client, SessionLocal = chat_client
    conversation_id = seed_conversation(
        SessionLocal,
        user_uid=EMPLOYEE_USER["uid"],
        title="Employee private",
    )

    response = client.delete(
        f"/api/conversations/{conversation_id}",
        headers=auth_headers("manager-token"),
    )

    assert response.status_code == 404

    db = SessionLocal()
    try:
        assert db.query(ConversationModel).count() == 1
    finally:
        db.close()


def test_delete_unknown_conversation_returns_404(
    chat_client: tuple[TestClient, sessionmaker],
) -> None:
    client, _ = chat_client

    response = client.delete(
        "/api/conversations/999999",
        headers=auth_headers("employee-token"),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation introuvable"


def test_messages_are_persisted_in_order(
    chat_client: tuple[TestClient, sessionmaker],
) -> None:
    client, SessionLocal = chat_client
    conversation_id = seed_conversation(
        SessionLocal,
        user_uid=EMPLOYEE_USER["uid"],
        title="Ordered",
    )

    response = client.get(
        f"/api/conversations/{conversation_id}",
        headers=auth_headers("employee-token"),
    )

    assert response.status_code == 200
    assert [
        message["role"]
        for message in response.json()["messages"]
    ] == [
        "user",
        "assistant",
    ]


def test_conversations_are_sorted_by_updated_at_desc(
    chat_client: tuple[TestClient, sessionmaker],
) -> None:
    client, SessionLocal = chat_client
    now = datetime.utcnow()
    seed_conversation(
        SessionLocal,
        user_uid=EMPLOYEE_USER["uid"],
        title="Older",
        updated_at=now - timedelta(days=1),
    )
    seed_conversation(
        SessionLocal,
        user_uid=EMPLOYEE_USER["uid"],
        title="Newer",
        updated_at=now,
    )

    response = client.get(
        "/api/conversations",
        headers=auth_headers("employee-token"),
    )

    assert response.status_code == 200
    assert [
        item["title"]
        for item in response.json()
    ] == [
        "Newer",
        "Older",
    ]


def test_history_is_available_from_new_db_session(
    chat_client: tuple[TestClient, sessionmaker],
) -> None:
    client, SessionLocal = chat_client
    conversation_id = seed_conversation(
        SessionLocal,
        user_uid=EMPLOYEE_USER["uid"],
        title="Persistent",
    )

    first_session = SessionLocal()
    first_session.close()

    response = client.get(
        f"/api/conversations/{conversation_id}",
        headers=auth_headers("employee-token"),
    )

    assert response.status_code == 200
    assert response.json()["messages"][0]["content"] == "Question Persistent"


def test_conversation_is_visible_from_new_client_with_same_database(
    chat_client: tuple[TestClient, sessionmaker],
) -> None:
    client, SessionLocal = chat_client

    create_response = client.post(
        "/api/chat",
        headers=auth_headers("employee-token"),
        json={
            "message": "Question persistante",
        },
    )

    assert create_response.status_code == 200
    conversation_id = create_response.json()["conversation_id"]

    restarted_client = TestClient(app)
    response = restarted_client.get(
        "/api/conversations",
        headers=auth_headers("employee-token"),
    )

    assert response.status_code == 200
    assert any(
        item["id"] == conversation_id
        for item in response.json()
    )

    db = SessionLocal()
    try:
        assert (
            db.query(ChatMessageModel)
            .filter(ChatMessageModel.conversation_id == conversation_id)
            .count()
            == 2
        )
    finally:
        db.close()


def test_post_chat_persists_user_and_assistant_messages(
    chat_client: tuple[TestClient, sessionmaker],
) -> None:
    client, SessionLocal = chat_client

    response = client.post(
        "/api/chat",
        headers=auth_headers("employee-token"),
        json={
            "message": "Bonjour",
        },
    )

    assert response.status_code == 200
    conversation_id = response.json()["conversation_id"]

    db = SessionLocal()
    try:
        messages = (
            db.query(ChatMessageModel)
            .filter(
                ChatMessageModel.conversation_id == conversation_id
            )
            .order_by(ChatMessageModel.id.asc())
            .all()
        )
    finally:
        db.close()

    assert [
        message.role
        for message in messages
    ] == [
        "user",
        "assistant",
    ]
    assert messages[0].content == "Bonjour"
    assert messages[1].content == "Réponse à: Bonjour"


def test_post_chat_rejects_other_user_conversation_id(
    chat_client: tuple[TestClient, sessionmaker],
) -> None:
    client, SessionLocal = chat_client
    conversation_id = seed_conversation(
        SessionLocal,
        user_uid=EMPLOYEE_USER["uid"],
        title="Employee private",
    )

    response = client.post(
        "/api/chat",
        headers=auth_headers("manager-token"),
        json={
            "message": "Bonjour",
            "conversation_id": conversation_id,
        },
    )

    assert response.status_code == 404


def test_post_chat_leave_tool_result_is_persisted(
    chat_client: tuple[TestClient, sessionmaker],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, SessionLocal = chat_client

    async def fake_run_agent(
        message: str,
        tools: list[Any],
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        return {
            "answer": (
                "Votre demande REQ-123 a bien été créée et transmise "
                "au manager. Statut: pending."
            ),
            "tools_used": [
                "soumettre_demande_conge",
            ],
        }

    monkeypatch.setattr(
        chat_routes.chat_service,
        "run_agent",
        fake_run_agent,
    )

    response = client.post(
        "/api/chat",
        headers=auth_headers("employee-token"),
        json={
            "message": "Pose-moi un congé annuel du 3 au 5 septembre",
        },
    )

    assert response.status_code == 200
    conversation_id = response.json()["conversation_id"]

    db = SessionLocal()
    try:
        assistant_message = (
            db.query(ChatMessageModel)
            .filter(
                ChatMessageModel.conversation_id == conversation_id,
                ChatMessageModel.role == "assistant",
            )
            .one()
        )
    finally:
        db.close()

    assert "REQ-123" in assistant_message.content
    assert response.json()["tools_used"] == [
        "soumettre_demande_conge",
    ]


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("get", "/api/conversations"),
        ("post", "/api/conversations"),
        ("get", "/api/conversations/1"),
        ("delete", "/api/conversations/1"),
        ("post", "/api/chat"),
    ],
)
def test_chat_endpoints_without_auth_return_401(
    chat_client: tuple[TestClient, sessionmaker],
    method: str,
    url: str,
) -> None:
    client, _ = chat_client
    kwargs: dict[str, Any] = {}

    if method == "post" and url == "/api/chat":
        kwargs["json"] = {
            "message": "Bonjour",
        }

    response = getattr(client, method)(
        url,
        **kwargs,
    )

    assert response.status_code == 401


def test_openapi_declares_global_firebase_bearer_auth(
    chat_client: tuple[TestClient, sessionmaker],
) -> None:
    client, _ = chat_client

    openapi = client.get("/openapi.json").json()

    assert openapi["components"]["securitySchemes"]["FirebaseBearer"] == {
        "type": "http",
        "description": (
            "Token Firebase ID au format Bearer. "
            "Utilisez le bouton Authorize de Swagger."
        ),
        "scheme": "bearer",
    }
    assert {
        "FirebaseBearer": []
    } in openapi["paths"]["/api/conversations"]["get"]["security"]
    summary_examples = openapi["components"]["schemas"][
        "ConversationSummaryResponse"
    ]["examples"]
    assert summary_examples[0]["id"] == 12
    assert summary_examples[0]["title"] == "Questions RH"
