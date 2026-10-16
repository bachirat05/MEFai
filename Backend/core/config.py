from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings
from pydantic import field_validator

# Project root: .../Cortex_AI_Minist-re-main (parent of Backend/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Backend package directory: .../Cortex_AI_Minist-re-main/Backend
BACKEND_DIR = BASE_DIR / "Backend"


class Settings(BaseSettings):

    ollama_embedding_model: str = "nomic-embed-text"
    ollama_base_url: str = "http://localhost:11434"

    chroma_persist_dir: str = str(BASE_DIR / "chroma_db")
    chroma_collection_name: str = "rh_documents"

    n8n_webhook_url: str = ""

    # Webhooks spécifiques par workflow
    n8n_webhook_conge_url: str = ""
    n8n_status_notification_webhook_url: str = ""
    n8n_webhook_document_url: str = ""

    n8n_secret_token: str = ""
    n8n_timeout_seconds: float = 15.0
    n8n_status_notification_webhook_url: str = ""

    server_port: int = 8000

    model_config = {
        "env_file": str(BACKEND_DIR / ".env"),
        "extra": "ignore",
        "env_file_encoding": "utf-8",
    }

    @field_validator("chroma_persist_dir")
    @classmethod
    def normalize_chroma_persist_dir(cls, value: str) -> str:
        path = Path(value)

        if not path.is_absolute():
            path = BASE_DIR / path

        return str(path.resolve())


def get_settings() -> Settings:
    return Settings()