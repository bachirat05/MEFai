# Fichier pour préparer et sécuriser la réponse finale
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

DOCUMENT_FALLBACK_ANSWER = (
    "Les documents internes actuels "
    "ne précisent pas cette information."
)

# détecte la réponse générique indiquant que les documents ne précisent pas l'information
def is_document_fallback_answer(
    answer: str,
) -> bool:
    normalized = " ".join(
        answer.strip().lower().split()
    )
    expected = " ".join(
        DOCUMENT_FALLBACK_ANSWER.lower().split()
    )
    return expected in normalized

# extrait le premier résultat documentaire et peut construire une réponse directement à partir de son contenu
def build_answer_from_preloaded_context(
    context: str,
    query: str | None = None,
) -> str | None:
    if (
        not context.strip()
        or context.lstrip().startswith(
            "Aucun document trouvé"
        )
        or context.lstrip().startswith("Error:")
    ):
        return None

    match = re.search(
        r"--- R[ée]sultat 1.*?---\n(?P<body>.*?)(?=\n--- R[ée]sultat 2|\Z)",
        context,
        flags=re.DOTALL,
    )

    if match is None:
        return None

    body = match.group("body").strip()

    if not body:
        return None

    source_line = ""
    content = body

    if body.startswith("[Source:"):
        source_end = body.find("]\n")
        if source_end != -1:
            source_line = body[: source_end + 1]
            content = body[source_end + 2 :].strip()

    if not content:
        return None

    if query:
        extracted = extract_relevant_context_excerpt(
            content,
            query,
        )

        if extracted:
            content = extracted

    answer = (
        "D'après les documents internes :\n\n"
        f"{content}"
    )

    if source_line:
        answer = (
            f"{answer}\n\n{source_line}"
        )

    return answer

# sélectionne des phrases contenant des mots-clés de la question
def extract_relevant_context_excerpt(
    content: str,
    query: str,
) -> str | None:
    ignored = {
        "quel",
        "quelle",
        "quels",
        "quelles",
        "combien",
        "dans",
        "pour",
        "est",
        "sont",
        "faut",
        "faire",
        "cette",
        "politique",
    }
    query_tokens = {
        token
        for token in re.findall(
            r"[a-zA-ZÀ-ÿ0-9]{3,}",
            query.lower(),
        )
        if token not in ignored
    }

    if not query_tokens:
        return None

    units = [
        unit.strip()
        for unit in re.split(
            r"(?<=[.!?])\s+|\n+",
            content,
        )
        if unit.strip()
    ]
    selected: list[str] = []

    for index, unit in enumerate(units):
        unit_tokens = {
            token
            for token in re.findall(
                r"[a-zA-ZÀ-ÿ0-9]{3,}",
                unit.lower(),
            )
        }

        if not (query_tokens & unit_tokens):
            continue

        selected.append(unit)

        if (
            index + 1 < len(units)
            and re.match(
                r"^\d+\.",
                unit,
            )
        ):
            selected.append(
                units[index + 1]
            )

    if not selected:
        return None

    deduped: list[str] = []

    for unit in selected:
        if unit not in deduped:
            deduped.append(unit)

    return "\n".join(
        deduped[:4]
    )

# supprime les puces vides et les espaces
def remove_empty_bullet_lines(
    answer: str,
) -> str:
    lines = [
        line
        for line in answer.splitlines()
        if line.strip() not in {
            "-",
            "*",
            "•",
        }
    ]

    cleaned = "\n".join(lines)
    cleaned = re.sub(
        r"(?im)^.*\b(?:notamment|sources?)\s*:\s*$",
        "",
        cleaned,
    )
    cleaned = re.sub(
        r"\n{3,}",
        "\n\n",
        cleaned,
    )

    return cleaned.strip()

# identifie les questions qui nécessitent une réponse particulièrement ancrée dans les documents, comme celles portant sur un montant ou un code
def should_use_extractive_grounding(
    message: str,
) -> bool:
    normalized = message.lower()
    markers = (
        "combien",
        "montant",
        "code",
        "référence",
        "reference",
        "délai",
        "delai",
        "renouvel",
        "panne",
        "vol",
        "perte",
        "interdit",
        "que faut-il faire",
        "doit",
    )
    return any(
        marker in normalized
        for marker in markers
    )