# Fichier pour détection des questions de suivi et enrichissement de la recherche avec l’historique
# C'est le module qui répond à cette difficulté : une question peut être incompréhensible si on la sépare de la conversation précédente

from __future__ import annotations

import logging
import re
from typing import Any

from chat.question_analyzer import (
    is_document_question,
    extract_search_subject,
)

logger = logging.getLogger(__name__)

FOLLOW_UP_MARKERS = (
    "cette politique",
    "ce document",
    "ce montant",
    "ce délai",
    "ce delai",
    "dans ce cas",
    "combien",
    "quel montant",
    "quel code",
    "code de référence",
    "code de reference",
)

def is_follow_up_question(
        self,
        message: str,
    ) -> bool:
        normalized = message.lower()
        return any(
            marker in normalized
            for marker in FOLLOW_UP_MARKERS
        )

# utilise l'historique pour construire une requête enrichie
def build_contextual_search_query(
        self,
        message: str,
        history: list[dict[str, str]] | None,
    ) -> str:
        if (
            not history
            or not is_follow_up_question(
                message
            )
        ):
            return message

        previous_subjects: list[str] = []
        previous_files: list[str] = []

        for item in reversed(history):
            if item.get("role") == "assistant":
                previous_files.extend(
                    re.findall(
                        r"File:\s*([^\]\|]+)",
                        item.get("content", ""),
                    )
                )
                continue

            if item.get("role") != "user":
                continue

            content = " ".join(
                item.get("content", "").split()
            )

            if not content:
                continue

            if is_document_question(
                content
            ):
                subject = extract_search_subject(
                    content
                )

                if subject:
                    previous_subjects.append(subject)

            if len(previous_subjects) >= 2:
                break

        context_parts = [
            *reversed(previous_subjects),
            *[
                file_name.strip()
                for file_name in previous_files[:2]
                if file_name.strip()
            ],
        ]

        if not context_parts:
            return message

        context = " ".join(
            context_parts
        )

        return (
            f"{message}\n\n"
            "Contexte conversationnel récent: "
            f"{context}"
        )
