
from __future__ import annotations

import logging
import re
import unicodedata

from mcp.server import MCPServer

from Backend.sqlite.database import SessionLocal
from core.config import get_settings
from core.logging import setup_logging
from schemas.document import DocumentCategory, DocumentSearchQuery
from schemas.workflow import DemandeConge
from services.rag.rag_service import (
    RAGInitializationError,
    RAGService,
)
from services.workflows.n8n_service import N8nService, N8nServiceError
from services.workflows.leave_submission_service import (
    NoManagerAvailableError,
    submit_leave_request,
)

setup_logging()
logger = logging.getLogger(__name__)
settings = get_settings()

mcp_server = MCPServer("congés-agent", version="1.0.0")

# Les services sont initialisés dans main.py au démarrage de FastAPI.
rag_service: RAGService | None = None
n8n_service: N8nService | None = None


def set_services(
    rag: RAGService | None,
    n8n: N8nService | None,
) -> None:
    """Reçoit les instances des services initialisés par main.py."""
    global rag_service, n8n_service
    rag_service = rag
    n8n_service = n8n


# =========================================================
# HELPERS DE RECHERCHE UTILISÉS PAR search_documents
# =========================================================

def normalize_document_search_category(
    query: str,
    category: str | None,
) -> str | None:
    normalized_query = query.lower()
    training_markers = ("formation", "certification", "certificat", "certif")

    if (
        category == DocumentCategory.HR_PROCEDURE.value
        and any(marker in normalized_query for marker in training_markers)
    ):
        return DocumentCategory.TRAINING.value

    return category


def is_training_process_query(query: str, category: str | None) -> bool:
    normalized_query = query.lower()
    training_markers = ("formation", "certification", "certificat", "certif")
    process_markers = (
        "soumettre", "demande", "délai", "delai", "préavis", "preavis",
        "quand", "combien de jours", "responsable", "qui", "intervient",
        "valider", "validation", "étape", "etape", "inscription",
    )

    return (
        category == DocumentCategory.TRAINING.value
        and any(marker in normalized_query for marker in training_markers)
        and any(marker in normalized_query for marker in process_markers)
    )


def rank_process_results(query: str, results):
    normalized_query = query.lower()

    def score(result) -> int:
        content = result.content.lower()
        rank_score = 0

        process_terms = (
            "étape", "etape", "responsable", "délai cible",
            "delai cible", "action:",
        )
        rank_score += sum(1 for term in process_terms if term in content) * 4

        if any(term in normalized_query for term in (
            "soumettre", "quand", "préavis", "preavis", "délai",
            "delai", "combien de jours", "inscription",
        )):
            rank_score += sum(1 for term in (
                "soumettre", "avant la session", "délai cible", "delai cible",
            ) if term in content) * 3

        if any(term in normalized_query for term in (
            "manager", "valider", "validation", "responsable", "qui", "intervient",
        )):
            rank_score += sum(1 for term in (
                "manager", "responsable", "rh / administration", "valider ou refuser",
            ) if term in content) * 3

        return rank_score

    return sorted(
        results,
        key=lambda result: (score(result), result.score),
        reverse=True,
    )


def normalize_for_lexical_match(value: str) -> str:
    return (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )


def lexical_tokens(value: str) -> set[str]:
    stop_words = {
        "avec", "dans", "des", "du", "elle", "est", "les", "leur",
        "pour", "que", "quel", "quelle", "quels", "quelles", "qui",
        "une", "un", "sur", "par", "de", "la", "le", "l", "d", "a",
        "au", "aux", "ce", "ces", "se", "sa", "son",
    }
    tokens = set(re.findall(r"[a-z0-9]{3,}", normalize_for_lexical_match(value)))
    return {token for token in tokens if token not in stop_words}


PRECISION_MARKERS = {
    "code", "reference", "identifiant", "montant", "indemnite", "prime",
    "plafond", "maximum", "mad", "jours", "mois", "pourcentage", "date",
    "duree", "limite", "ville", "ordinateur", "professionnel",
    "professionnelle", "accessoire", "informatique", "equipement",
    "materiel", "panne", "incident", "support", "vol", "perte",
    "renouvellement", "renouvele", "remboursable", "signaler",
}

LEXICAL_EQUIVALENTS = {
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


def expand_tokens(tokens: set[str]) -> set[str]:
    expanded = set(tokens)
    for token in tokens:
        expanded.update(LEXICAL_EQUIVALENTS.get(token, set()))
    return expanded


def precision_value_patterns(value: str) -> set[str]:
    normalized = normalize_for_lexical_match(value)
    patterns: set[str] = set()

    if re.search(r"\b[A-Z0-9]{2,}(?:-[A-Z0-9]{2,})+\b", value):
        patterns.add("code_like")
    if re.search(r"\b\d[\d\s.,]*\s*(?:mad|dh|dirhams?|%)\b", normalized):
        patterns.add("money_or_percent")
    if re.search(r"\b\d+\s*(?:jours?|mois|annees?|ans)\b", normalized):
        patterns.add("duration")
    if re.search(r"\b\d+\b", normalized):
        patterns.add("number")

    return patterns


def rerank_document_results(query: str, results):
    query_tokens = expand_tokens(lexical_tokens(query))
    query_precision_markers = query_tokens & PRECISION_MARKERS
    query_patterns = precision_value_patterns(query)

    def rank_key(result):
        content_tokens = expand_tokens(lexical_tokens(result.content))
        metadata_text = " ".join([
            result.metadata.filename or "",
            result.metadata.document_type or "",
            " ".join(result.metadata.tags),
        ])
        metadata_tokens = expand_tokens(lexical_tokens(metadata_text))
        lexical_overlap = len(query_tokens & (content_tokens | metadata_tokens))
        content_patterns = precision_value_patterns(result.content)
        precision_overlap = len(query_precision_markers & content_tokens)
        inferred_precision = 0

        if query_precision_markers and content_patterns:
            inferred_precision += 1
        if "montant" in query_precision_markers and (
            "money_or_percent" in content_patterns or "mad" in content_tokens
        ):
            inferred_precision += 3
        if (
            {"code", "reference", "identifiant"} & query_precision_markers
            and "code_like" in content_patterns
        ):
            inferred_precision += 3
        if (
            {"jours", "mois", "duree"} & query_precision_markers
            and "duration" in content_patterns
        ):
            inferred_precision += 2
        if query_patterns and query_patterns & content_patterns:
            inferred_precision += 2

        return (
            inferred_precision,
            precision_overlap,
            lexical_overlap,
            result.score,
        )

    return sorted(results, key=rank_key, reverse=True)


def has_lexical_overlap(query: str, results) -> bool:
    query_tokens = lexical_tokens(query)
    if not query_tokens:
        return bool(results)

    for result in results:
        result_tokens = lexical_tokens(" ".join([
            result.content,
            result.metadata.filename or "",
            " ".join(result.metadata.tags),
        ]))
        if query_tokens & result_tokens:
            return True

    return False


def merge_search_results(*result_lists):
    merged = {}
    for results in result_lists:
        for result in results:
            existing = merged.get(result.document_id)
            if existing is None or result.score > existing.score:
                merged[result.document_id] = result
    return list(merged.values())


def describe_search_results(results) -> list[dict[str, object]]:
    return [
        {
            "rank": index,
            "document_id": result.document_id,
            "score": result.score,
            "category": result.metadata.category.value,
            "preview": result.content[:500],
        }
        for index, result in enumerate(results, start=1)
    ]


# =========================================================
# OUTIL MCP — RECHERCHE DOCUMENTAIRE
# =========================================================

@mcp_server.tool()
async def search_documents(
    query: str,
    category: str | None = None,
    department: str | None = None,
    top_k: int = 8,
    similarity_threshold: float = 0.35,
) -> str:
    """Recherche sémantique dans la base documentaire RH du MEF."""

    if rag_service is None or not rag_service.is_initialized:
        return "Error: RAG service is not initialized."

    category = normalize_document_search_category(query, category)

    logger.info(
        "search_documents routing | query=%r | category=%r | top_k=%s | threshold=%s",
        query, category, top_k, similarity_threshold,
    )

    search_category = None
    if category is not None:
        try:
            search_category = DocumentCategory(category)
        except Exception:
            valid = [item.value for item in DocumentCategory]
            return f"Error: invalid category '{category}'. Valid values: {valid}"

    effective_threshold = min(max(similarity_threshold, 0.0), 0.5)
    effective_top_k = max(top_k, 8)
    candidate_top_k = max(effective_top_k, 30)

    search_query = DocumentSearchQuery(
        query=query,
        category=search_category,
        department=department,
        tags=[],
        top_k=candidate_top_k,
        similarity_threshold=effective_threshold,
    )

    try:
        response = rag_service.search(search_query)

        logger.info(
            "search_documents raw results | query=%r | category=%r | results=%s",
            query, category, describe_search_results(response),
        )

        if not response and search_category == DocumentCategory.HR_PROCEDURE:
            search_category = DocumentCategory.TRAINING
            category = DocumentCategory.TRAINING.value
            search_query = DocumentSearchQuery(
                query=query,
                category=search_category,
                department=department,
                tags=[],
                top_k=candidate_top_k,
                similarity_threshold=effective_threshold,
            )
            response = rag_service.search(search_query)

            logger.info(
                "search_documents fallback raw results | query=%r | category=%r | results=%s",
                query, category, describe_search_results(response),
            )

        if search_category is not None and (
            not response or not has_lexical_overlap(query, response)
        ):
            global_query = DocumentSearchQuery(
                query=query,
                category=None,
                department=department,
                tags=[],
                top_k=candidate_top_k,
                similarity_threshold=effective_threshold,
            )
            global_response = rag_service.search(global_query)
            logger.info(
                "search_documents global fallback raw results | query=%r | results=%s",
                query, describe_search_results(global_response),
            )
            response = merge_search_results(response, global_response)

        process_reranked = False
        if response and is_training_process_query(query, category):
            response = rank_process_results(query, response)
            process_reranked = True
            logger.info(
                "search_documents reranked results | query=%r | category=%r | results=%s",
                query, category, describe_search_results(response),
            )

        if response and not process_reranked:
            response = rerank_document_results(query, response)
            response = response[:effective_top_k]

        if not response:
            return (
                f"Aucun document trouvé pour la requête : '{query}' "
                "après recherche catégorisée et recherche globale."
            )

        lines = [
            f"Résultats pour '{query}' (catégorie: {category or 'non spécifiée'}):",
            "",
        ]

        source_labels = {"internal_wiki": "Documentation RH interne"}
        category_labels = {
            "leave_policy": "Politique de congés",
            "benefits": "Avantages et indemnités",
            "rh_policy": "Politique RH",
            "hr_procedure": "Procédure RH",
            "training": "Formation",
            "onboarding": "Intégration",
            "compliance": "Conformité",
            "other": "Autre",
        }

        for idx, result in enumerate(response, start=1):
            source_value = result.metadata.source.value
            category_value = result.metadata.category.value
            filename = (
                result.metadata.filename
                or ", ".join(result.metadata.tags[:1])
                or result.document_id
            )
            source = source_labels.get(source_value, source_value)
            cat = category_labels.get(category_value, category_value)
            content_block = (
                f"[Source: {source} | Category: {cat} | File: {filename}]\n"
                f"{result.content}"
            )
            lines.append(f"--- Résultat {idx} (score: {result.score:.4f}) ---")
            lines.append(content_block)
            lines.append("")

        return "\n".join(lines)

    except RAGInitializationError as exc:
        logger.error("RAG not initialized during search: %s", exc)
        return f"Error: RAG service not initialized — {exc}"
    except Exception as exc:
        logger.error("Search error: %s", exc)
        return f"Error during search: {exc}"


# =========================================================
# OUTIL MCP — DEMANDE DE CONGÉ
# =========================================================

@mcp_server.tool()
async def soumettre_demande_conge(
    employe_id: str,
    date_debut: str,
    date_fin: str,
    type_conge: str,
    motif: str,
    user_uid: str | None = None,
    employee_email: str | None = None,
    user_role: str | None = None,
) -> str:
    if n8n_service is None:
        return "Error: N8n service is not initialized."

    try:
        demande = DemandeConge(
            employe_id=employe_id,
            date_debut=date_debut,
            date_fin=date_fin,
            type_conge=type_conge,
            motif=motif,
        )
    except Exception as exc:
        return f"Error: validation failed — {exc}"

    try:
        if not user_uid:
            return "Error: authenticated user context is required."

        db = SessionLocal()
        try:
            response = await submit_leave_request(
                demande=demande,
                user={
                    "uid": user_uid,
                    "email": employee_email or "",
                    "role": user_role or "",
                },
                db=db,
                n8n_service=n8n_service,
            )
        finally:
            db.close()

        return (
            f"Votre demande {response.demande_id} a bien été créée et transmise au manager. "
            f"Statut: {response.statut}. "
            f"Période: {demande.date_debut} au {demande.date_fin}. "
            f"Type de congé: {demande.type_conge.value}."
        )

    except NoManagerAvailableError as exc:
        return f"Error: impossible de créer la demande — {exc}"
    except N8nServiceError as exc:
        logger.error("n8n workflow error: %s", exc)
        return f"Error: n8n workflow failed — {exc}"
    except Exception as exc:
        logger.error("Unexpected error submitting leave request: %s", exc)
        return f"Error: unexpected failure — {exc}"
