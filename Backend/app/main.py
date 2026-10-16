
from __future__ import annotations

import logging
import sys

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from Backend.sqlite.database import Base, engine
from Backend.sqlite.activity_models import ActivityLogModel
from Backend.sqlite.chat_models import ChatMessageModel, ConversationModel
from Backend.sqlite.leave_models import LeaveRequestModel

from core.config import get_settings
from core.logging import setup_logging

from services.rag.rag_service import (
    RAGService,
    RAGServiceError,
)
from services.workflows.n8n_service import (
    N8nService,
    N8nServiceError,
)

from app.firebase_auth import require_admin

from api.routes.chat import router as chat_router
from api.routes.conges import router as conges_router
from api.routes.documents import router as documents_router
from api.routes.system import router as system_router

from sqlite.init_db import initialize_database

from services.audit.activity_log_service import ensure_activity_log_indexes

# Import du serveur MCP et de sa fonction de connexion aux services.
from services.mcp.mcp_server import mcp_server, set_services


# =========================================================
# PATH
# =========================================================

ROOT_DIR = Path(__file__).resolve().parent.parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


# =========================================================
# LANGCHAIN / OLLAMA
# =========================================================

try:
    from langchain_community.embeddings import OllamaEmbeddings
except ImportError as exc:
    raise ImportError(
        "langchain-community is required. "
        "Install it with: pip install langchain-community"
    ) from exc


# =========================================================
# LOGGING + SETTINGS
# =========================================================

setup_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


# =========================================================
# SERVICES STATE
# =========================================================

rag_service: RAGService | None = None
n8n_service: N8nService | None = None


# =========================================================
# SERVICE BUILDERS
# =========================================================

def _build_rag_service() -> RAGService:
    embedding = OllamaEmbeddings(
        model=settings.ollama_embedding_model,
        base_url=settings.ollama_base_url,
    )

    rag = RAGService(
        embedding_function=embedding,
        persist_directory=settings.chroma_persist_dir,
        collection_name=settings.chroma_collection_name,
    )

    rag.initialize()
    return rag


def _build_n8n_service() -> N8nService:
    return N8nService(
        webhook_url=settings.n8n_webhook_url,
        secret_token=settings.n8n_secret_token,
        timeout_seconds=settings.n8n_timeout_seconds,
    )


# =========================================================
# LIFESPAN
# =========================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    global rag_service, n8n_service

    rag_service = _build_rag_service()
    n8n_service = _build_n8n_service()

    # Transmet les services au module MCP sans déplacer
    # leur initialisation hors de main.py.
    set_services(
        rag=rag_service,
        n8n=n8n_service,
    )

    app.state.rag_service = rag_service
    app.state.n8n_service = n8n_service

    logger.info(
        "Congés MCP Agent started — RAG service ready, n8n service ready"
    )

    try:
        yield
    finally:
        app.state.rag_service = None
        app.state.n8n_service = None

        rag_service = None
        n8n_service = None

        # Évite de conserver les références après l'arrêt de l'application.
        set_services(rag=None, n8n=None)

        logger.info("Congés MCP Agent stopped")


# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(
    title="Congés MCP Agent",
    version="1.0.0",
    description=(
        "MCP server exposing RAG-based document search "
        "and leave submission via n8n."
    ),
    lifespan=lifespan,
)


# =========================================================
# DATABASE TABLES : initialisation
# =========================================================
initialize_database()

# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# HEALTH
# =========================================================

@app.get("/health", tags=["health"])
async def health() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "ok",
            "rag_initialized": (
                rag_service is not None
                and rag_service.is_initialized
            ),
            "n8n_configured": (
                n8n_service is not None
                and bool(settings.n8n_webhook_url)
            ),
        },
    )


# =========================================================
# EXCEPTION HANDLERS
# =========================================================

@app.exception_handler(RAGServiceError)
async def rag_error_handler(
    request: Request,
    exc: RAGServiceError,
) -> JSONResponse:
    logger.error(
        "RAG service error on %s: %s",
        request.url.path,
        exc,
    )

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "RAG service unavailable",
            "detail": str(exc),
        },
    )


@app.exception_handler(N8nServiceError)
async def n8n_error_handler(
    request: Request,
    exc: N8nServiceError,
) -> JSONResponse:
    logger.error(
        "n8n service error on %s: %s",
        request.url.path,
        exc,
    )

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "n8n workflow service unavailable",
            "detail": str(exc),
        },
    )


@app.exception_handler(Exception)
async def generic_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.exception("Unhandled error on %s", request.url.path)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
        },
    )


# =========================================================
# ADMIN TEST
# =========================================================

@app.get("/api/admin/test")
async def admin_test(user=Depends(require_admin)):
    return {
        "status": "ok",
        "message": "Admin access granted",
        "email": user.get("email"),
        "role": user.get("role"),
    }


# =========================================================
# ROUTERS
# =========================================================

app.include_router(chat_router)
app.include_router(conges_router)
app.include_router(documents_router)
app.include_router(system_router)


# =========================================================
# MCP
# =========================================================

app.mount(
    "/mcp",
    mcp_server.sse_app(
        sse_path="/sse",
        message_path="/messages/",
    ),
)
