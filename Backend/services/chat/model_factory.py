# Fichier pour l'initialisation et récupération du modèle Ollama
import logging

from langchain_ollama import ChatOllama

logger = logging.getLogger(__name__)


def build_model() -> ChatOllama:
    """Initialise le modèle local exécuté via Ollama."""

    model_name = "qwen3:8b"

    logger.info(
        "Initializing local Ollama model: %s",
        model_name,
    )

    return ChatOllama(
        model=model_name,
        base_url="http://127.0.0.1:11434",
        temperature=0,
    )