from __future__ import annotations

import logging
import re

from schemas.document import (
    DocumentSearchQuery,
    DocumentSearchResponse,
    DocumentSearchResult,
)
from services.rag.loader import normalize_text
from services.rag.rag_service import RAGRetrievalError, RAGService

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Vocabulaire du reranker
# ------------------------------------------------------------------

# Mots vides de 3 lettres ou plus (le tokenizer ignore déjà les mots plus courts).
_STOP_WORDS = {
    "avec", "dans", "des", "elle", "est", "les", "leur", "pour", "que",
    "quel", "quelle", "quels", "quelles", "qui", "une", "sur", "par",
    "aux", "ces", "son",
}

# Chaque groupe est déclaré une seule fois ; les équivalences sont symétriques.
_SYNONYM_GROUPS = [
    {"ans", "annee", "annees"},
    {"renouvele", "renouvellement", "renouveler"},
    {"professionnel", "professionnelle", "professionnels"},
    {"equipement", "materiel", "ordinateur", "portable"},
    {"panne", "incident", "support"},
    {"vol", "perte"},
    {"montant", "plafond", "maximum", "remboursable"},
]
_TOKEN_EQUIVALENTS = {token: group for group in _SYNONYM_GROUPS for token in group}

_PRECISION_MARKERS = {
    "code", "reference", "identifiant", "montant", "indemnite", "prime",
    "plafond", "maximum", "mad", "jours", "mois", "pourcentage", "date",
    "duree", "limite", "ville", "ordinateur", "professionnel",
    "professionnelle", "accessoire", "informatique", "equipement", "materiel",
    "panne", "incident", "support", "vol", "perte", "renouvellement",
    "renouvele", "remboursable", "signaler",
}
_CODE_MARKERS = {"code", "reference", "identifiant"}
_DURATION_MARKERS = {"jours", "mois", "duree"}

_TOKEN_RE = re.compile(r"[a-z0-9]{3,}")
_CODE_RE = re.compile(r"\b[A-Z0-9]{2,}(?:-[A-Z0-9]{2,})+\b")  # appliqué au texte brut
_MONEY_RE = re.compile(r"\b\d[\d\s.,]*\s*(?:mad|dh|dirhams?|%)\b")
_DURATION_RE = re.compile(r"\b\d+\s*(?:jours?|mois|annees?|ans|heures?)\b")
_NUMBER_RE = re.compile(r"\b\d+\b")


# ------------------------------------------------------------------
# Reranking
# ------------------------------------------------------------------


def lexical_tokens(value: str) -> set[str]:
    tokens = {t for t in _TOKEN_RE.findall(normalize_text(value)) if t not in _STOP_WORDS}
    for token in list(tokens):
        tokens |= _TOKEN_EQUIVALENTS.get(token, set())
    return tokens


def _value_patterns(value: str) -> set[str]:
    normalized = normalize_text(value)
    patterns: set[str] = set()
    if _CODE_RE.search(value):
        patterns.add("code_like")
    if _MONEY_RE.search(normalized):
        patterns.add("money_or_percent")
    if _DURATION_RE.search(normalized):
        patterns.add("duration")
    if _NUMBER_RE.search(normalized):
        patterns.add("number")
    return patterns


def _precision_bonus(
    query_markers: set[str],
    query_patterns: set[str],
    result_tokens: set[str],
    result_patterns: set[str],
) -> int:
    bonus = 0
    if query_markers and result_patterns:
        bonus += 1
    if "montant" in query_markers and ("money_or_percent" in result_patterns or "mad" in result_tokens):
        bonus += 3
    if query_markers & _CODE_MARKERS and "code_like" in result_patterns:
        bonus += 3
    if query_markers & _DURATION_MARKERS and "duration" in result_patterns:
        bonus += 2
    if query_patterns & result_patterns:
        bonus += 2
    return bonus


def rerank(
    query_text: str,
    results: list[DocumentSearchResult],
    top_k: int,
) -> list[DocumentSearchResult]:
    query_tokens = lexical_tokens(query_text)
    query_markers = query_tokens & _PRECISION_MARKERS
    query_patterns = _value_patterns(query_text)

    def rank_key(result: DocumentSearchResult) -> tuple:
        meta = result.metadata
        result_tokens = lexical_tokens(
            f"{result.content}\n{meta.filename or ''} {meta.document_type or ''}"
        )
        bonus = _precision_bonus(
            query_markers,
            query_patterns,
            result_tokens,
            _value_patterns(result.content),
        )
        return (
            bonus,
            len(query_markers & result_tokens),
            len(query_tokens & result_tokens),
            result.score,
        )

    return sorted(results, key=rank_key, reverse=True)[:top_k]


# ------------------------------------------------------------------
# Retriever
# ------------------------------------------------------------------


class Retriever:
    def __init__(self, rag: RAGService) -> None:
        self._rag = rag

    def search(self, query: DocumentSearchQuery) -> DocumentSearchResponse:
        try:
            candidates = self._rag.vector_search(query)
            results = rerank(query.query, candidates, query.top_k)
        except RAGRetrievalError:
            logger.exception("Recherche échouée — query='%.60s'", query.query)
            raise
        except Exception as exc:
            logger.exception("Reranking échoué — query='%.60s'", query.query)
            raise RAGRetrievalError(f"Échec de la recherche : {exc}") from exc

        logger.info(
            "Recherche OK — query='%.60s', candidats=%d, retournés=%d",
            query.query, len(candidates), len(results),
        )
        return DocumentSearchResponse(
            query=query.query,
            results=results,
            total_found=len(candidates),
            returned_count=len(results),
        )