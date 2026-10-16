from __future__ import annotations

import logging
import re
import unicodedata

from schemas.document import (
    DocumentSearchQuery,
    DocumentSearchResponse,
    DocumentSearchResult,
)
from services.rag.rag_service import RAGRetrievalError, RAGService

logger = logging.getLogger(__name__)


_STOP_WORDS = {
    "avec",
    "dans",
    "des",
    "du",
    "elle",
    "est",
    "les",
    "leur",
    "pour",
    "que",
    "quel",
    "quelle",
    "quels",
    "quelles",
    "qui",
    "une",
    "un",
    "sur",
    "par",
    "de",
    "la",
    "le",
    "l",
    "d",
    "a",
    "au",
    "aux",
    "ce",
    "ces",
    "se",
    "sa",
    "son",
}

_TOKEN_EQUIVALENTS = {
    "annees": {"ans", "annee", "annees"},
    "ans": {"ans", "annee", "annees"},
    "renouvele": {"renouvele", "renouvellement", "renouveler"},
    "renouvellement": {"renouvele", "renouvellement", "renouveler"},
    "professionnel": {"professionnel", "professionnelle", "professionnels"},
    "professionnelle": {"professionnel", "professionnelle", "professionnels"},
    "equipement": {"equipement", "materiel", "ordinateur"},
    "materiel": {"equipement", "materiel", "ordinateur"},
    "ordinateur": {"ordinateur", "portable", "materiel", "equipement"},
    "panne": {"panne", "incident", "support"},
    "vol": {"vol", "perte"},
    "perte": {"vol", "perte"},
    "montant": {"montant", "plafond", "maximum", "remboursable"},
}

_PRECISION_MARKERS = {
    "code",
    "reference",
    "identifiant",
    "montant",
    "indemnite",
    "prime",
    "plafond",
    "maximum",
    "mad",
    "jours",
    "mois",
    "pourcentage",
    "date",
    "duree",
    "limite",
    "ville",
    "ordinateur",
    "professionnel",
    "professionnelle",
    "accessoire",
    "informatique",
    "equipement",
    "materiel",
    "panne",
    "incident",
    "support",
    "vol",
    "perte",
    "renouvellement",
    "renouvele",
    "remboursable",
    "signaler",
}


def _normalize_for_match(value: str) -> str:
    return (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )


def _lexical_tokens(value: str) -> set[str]:
    tokens = set(
        re.findall(
            r"[a-z0-9]{3,}",
            _normalize_for_match(value),
        )
    )
    expanded = {
        token
        for token in tokens
        if token not in _STOP_WORDS
    }

    for token in list(expanded):
        expanded.update(
            _TOKEN_EQUIVALENTS.get(token, set())
        )

    return expanded


def _value_patterns(value: str) -> set[str]:
    normalized = _normalize_for_match(value)
    patterns: set[str] = set()

    if re.search(r"\b[A-Z0-9]{2,}(?:-[A-Z0-9]{2,})+\b", value):
        patterns.add("code_like")

    if re.search(r"\b\d[\d\s.,]*\s*(?:mad|dh|dirhams?|%)\b", normalized):
        patterns.add("money_or_percent")

    if re.search(r"\b\d+\s*(?:jours?|mois|annees?|ans|heures?)\b", normalized):
        patterns.add("duration")

    if re.search(r"\b\d+\b", normalized):
        patterns.add("number")

    return patterns


def rerank(
    query_text: str,
    search_results: list[DocumentSearchResult],
    top_k: int,
) -> list[DocumentSearchResult]:
    query_tokens = _lexical_tokens(
        query_text
    )
    query_precision_markers = (
        query_tokens
        & _PRECISION_MARKERS
    )
    query_patterns = _value_patterns(
        query_text
    )

    def rank_key(result: DocumentSearchResult) -> tuple:
        metadata_text = " ".join(
            [
                result.metadata.filename or "",
                result.metadata.document_type or "",
                " ".join(result.metadata.tags),
            ]
        )
        result_tokens = _lexical_tokens(
            f"{result.content}\n{metadata_text}"
        )
        result_patterns = _value_patterns(
            result.content
        )
        lexical_overlap = len(
            query_tokens
            & result_tokens
        )
        precision_overlap = len(
            query_precision_markers
            & result_tokens
        )
        inferred_precision = 0

        if (
            query_precision_markers
            and result_patterns
        ):
            inferred_precision += 1

        if (
            "montant" in query_precision_markers
            and (
                "money_or_percent" in result_patterns
                or "mad" in result_tokens
            )
        ):
            inferred_precision += 3

        if (
            {
                "code",
                "reference",
                "identifiant",
            }
            & query_precision_markers
            and "code_like" in result_patterns
        ):
            inferred_precision += 3

        if (
            {
                "jours",
                "mois",
                "duree",
                "heures",
                "annees",
                "ans",
            }
            & query_precision_markers
            and "duration" in result_patterns
        ):
            inferred_precision += 2

        if (
            query_patterns
            and query_patterns & result_patterns
        ):
            inferred_precision += 2

        return (
            inferred_precision,
            precision_overlap,
            lexical_overlap,
            result.score,
        )

    return sorted(
        search_results,
        key=rank_key,
        reverse=True,
    )[:top_k]


class Retriever:
    """Vector search (RAGService) + lexical re-ranking."""

    def __init__(self, rag: RAGService) -> None:
        self._rag = rag

    def search(self, query: DocumentSearchQuery) -> DocumentSearchResponse:
        candidates = self._rag.search(query)

        try:
            search_results = rerank(
                query.query,
                candidates,
                query.top_k,
            )
        except Exception as exc:
            logger.error("Search failed for query '%s…': %s", query.query[:60], exc)
            raise RAGRetrievalError(f"Search failed: {exc}") from exc

        logger.info(
            "Search completed — query='%s…', results=%d",
            query.query[:60],
            len(search_results),
        )
        return DocumentSearchResponse(
            query=query.query,
            results=search_results,
            total_found=len(search_results),
            returned_count=len(search_results),
        )