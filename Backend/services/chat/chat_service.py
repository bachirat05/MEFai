from __future__ import annotations

import logging
import re
from typing import Any

from langchain_core.tools import StructuredTool
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent

from core.config import get_settings
from Backend.services.mcp.mcp_client import (
    normalize_search_documents_arguments,
)

from chat.prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

DOCUMENT_FALLBACK_ANSWER = (
    "Les documents internes actuels "
    "ne précisent pas cette information."
)

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

DOCUMENT_VALUE_MARKERS = (
    "code",
    "référence",
    "reference",
    "identifiant",
    "montant",
    "indemnité",
    "indemnite",
    "prime",
    "plafond",
    "maximum",
    "mad",
    "jours",
    "mois",
    "pourcentage",
    "date",
    "durée",
    "duree",
    "limite",
    "ville",
    "ordinateur",
    "informatique",
    "équipement",
    "equipement",
    "matériel",
    "materiel",
    "accessoire",
    "panne",
    "support",
    "vol",
    "perte",
    "renouvellement",
    "renouvelé",
    "renouvele",
    "remboursable",
)



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


class ChatService:

    def __init__(self) -> None:
        self.model: ChatOllama | None = None
        self.settings = get_settings()

    def _build_model(self) -> ChatOllama:
        """
        Initialise Qwen exécuté localement avec Ollama.
        """

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

    def _get_model(self) -> ChatOllama:

        if self.model is None:
            self.model = self._build_model()

        return self.model

    def _find_search_documents_tool(
        self,
        tools: list[StructuredTool],
    ) -> StructuredTool | None:
        for tool in tools:
            if tool.name == "search_documents":
                return tool

        return None

    def _is_document_question(
        self,
        message: str,
    ) -> bool:
        normalized = message.lower()
        markers = (
            "politique",
            "procédure",
            "procedure",
            "règle",
            "regle",
            "avantage",
            "prime",
            "indemnité",
            "indemnite",
            "formation",
            "certification",
            "congé",
            "conge",
            "télétravail",
            "teletravail",
            "onboarding",
            "intégration",
            "integration",
            "mobilité",
            "mobilite",
            "remboursement",
            "délai",
            "delai",
            "code de référence",
            "code de reference",
            *DOCUMENT_VALUE_MARKERS,
        )
        action_markers = (
            "je veux poser",
            "soumets ma demande",
            "crée une demande",
            "creer une demande",
            "créer une demande",
        )

        return (
            any(marker in normalized for marker in markers)
            and not any(marker in normalized for marker in action_markers)
        )

    def _is_follow_up_question(
        self,
        message: str,
    ) -> bool:
        normalized = message.lower()
        return any(
            marker in normalized
            for marker in FOLLOW_UP_MARKERS
        )

    def _build_contextual_search_query(
        self,
        message: str,
        history: list[dict[str, str]] | None,
    ) -> str:
        if (
            not history
            or not self._is_follow_up_question(
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

            if self._is_document_question(
                content
            ):
                subject = self._extract_search_subject(
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

    def _extract_search_subject(
        self,
        message: str,
    ) -> str:
        normalized = message.lower()

        known_subjects = (
            "mobilité interne",
            "mobilite interne",
            "équipement informatique",
            "equipement informatique",
            "matériel informatique",
            "materiel informatique",
            "ordinateur professionnel",
            "formation",
            "certification",
            "congé",
            "conge",
            "télétravail",
            "teletravail",
            "onboarding",
            "intégration",
            "integration",
            "sécurité",
            "securite",
            "confidentialité",
            "confidentialite",
        )

        for subject in known_subjects:
            if subject in normalized:
                return subject

        words = re.findall(
            r"[a-zA-ZÀ-ÿ0-9]{4,}",
            normalized,
        )
        ignored = {
            "quel",
            "quelle",
            "quels",
            "quelles",
            "combien",
            "conditions",
            "politique",
            "document",
            "demande",
            "demandes",
            "reference",
            "référence",
            "montant",
            "code",
            "dans",
            "avec",
            "pour",
            "sont",
            "est",
            "cette",
            "interne",
        }
        subject_words = [
            word
            for word in words
            if word not in ignored
        ]

        return " ".join(
            subject_words[:4]
        )

    def _infer_document_category(
        self,
        message: str,
    ) -> str | None:
        normalized = message.lower()

        if any(
            marker in normalized
            for marker in (
                "mobilité",
                "mobilite",
                "ordinateur",
                "informatique",
                "équipement",
                "equipement",
                "matériel",
                "materiel",
                "accessoire",
                "panne",
                "support",
                "vol",
                "perte",
                "renouvellement",
                "renouvelé",
                "renouvele",
            )
        ):
            return None

        if any(
            marker in normalized
            for marker in (
                "formation",
                "certification",
                "certificat",
                "certif",
            )
        ):
            return "training"

        if any(
            marker in normalized
            for marker in (
                "congé",
                "conge",
                "leave",
            )
        ):
            if any(
                marker in normalized
                for marker in (
                    "étape",
                    "etape",
                    "procédure",
                    "procedure",
                    "validation",
                    "responsable",
                )
            ):
                return "hr_procedure"

            return "leave_policy"

        if any(
            marker in normalized
            for marker in (
                "code",
                "référence",
                "reference",
                "identifiant",
                "montant",
            )
        ):
            return None

        if any(
            marker in normalized
            for marker in (
                "avantage",
                "prime",
                "indemnité",
                "indemnite",
                "benefit",
                "remboursement",
            )
        ):
            return "benefits"

        if any(
            marker in normalized
            for marker in (
                "onboarding",
                "intégration",
                "integration",
            )
        ):
            return "onboarding"

        if any(
            marker in normalized
            for marker in (
                "conformité",
                "conformite",
                "sécurité",
                "securite",
                "confidentialité",
                "confidentialite",
            )
        ):
            return "compliance"

        if any(
            marker in normalized
            for marker in (
                "procédure",
                "procedure",
                "étape",
                "etape",
                "responsable",
                "validation",
            )
        ):
            return "hr_procedure"

        if any(
            marker in normalized
            for marker in (
                "politique",
                "télétravail",
                "teletravail",
            )
        ):
            return "rh_policy"

        return None

    async def _preload_document_context(
        self,
        message: str,
        tools: list[StructuredTool],
        history: list[dict[str, str]] | None = None,
    ) -> tuple[str | None, dict[str, Any] | None]:
        if not self._is_document_question(
            message
        ):
            return None, None

        search_tool = self._find_search_documents_tool(
            tools
        )

        if search_tool is None:
            logger.warning(
                "Training procedure intent detected but search_documents is unavailable"
            )
            return None, None

        category = self._infer_document_category(
            message
        )
        search_query = self._build_contextual_search_query(
            message,
            history,
        )

        search_args = normalize_search_documents_arguments(
            {
                "query": search_query,
                "category": category,
                "top_k": 8,
                "similarity_threshold": (
                    0.5
                    if category == "training"
                    else 0.35
                ),
            },
            original_message=message,
        )

        logger.info(
            "Document pre-search | original_message=%r | args=%s",
            message,
            search_args,
        )

        context = await search_tool.ainvoke(
            search_args
        )

        logger.info(
            "Document pre-search result | chars=%s | preview=%r",
            len(str(context)),
            str(context)[:1200],
        )

        return str(context), search_args

    async def run_agent(
        self,
        message: str,
        tools: list[StructuredTool],
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:

        # ---------------------------------------------------------
        # Validation
        # ---------------------------------------------------------

        if not message.strip():
            raise ValueError(
                "Le message ne peut pas être vide."
            )

        if not tools:
            raise RuntimeError(
                "Aucun outil MCP disponible."
            )

        # ---------------------------------------------------------
        # Model
        # ---------------------------------------------------------

        model = self._get_model()

        logger.info(
            "Using local Qwen model through Ollama"
        )

        preloaded_context, preloaded_args = (
            await self._preload_document_context(
                message,
                tools,
                history,
            )
        )

        # ---------------------------------------------------------
        # Agent
        # ---------------------------------------------------------

        agent = create_react_agent(
            model=model,
            tools=tools,
        )

        # ---------------------------------------------------------
        # Messages
        # ---------------------------------------------------------

        messages: list[tuple[str, str]] = [
            ("system", SYSTEM_PROMPT)
        ]

        if preloaded_context and preloaded_args:
            messages.append(
                (
                    "system",
                    (
                        "Recherche documentaire deja executee pour cette "
                        "question RH interne.\n"
                        f"Message utilisateur original: {message}\n"
                        "Outil: search_documents\n"
                        f"Arguments: {preloaded_args}\n"
                        "Resultats fournis par le RAG:\n"
                        f"{preloaded_context}\n\n"
                        "Reponds uniquement a partir de ces resultats. "
                        "N'utilise le fallback d'absence d'information que "
                        "si ces resultats ne contiennent pas l'information "
                        "demandee."
                    ),
                )
            )

        if history:

            for item in history:

                role = item.get("role")
                content = item.get("content", "")

                if not content:
                    continue

                if role == "user":

                    messages.append(
                        ("human", content)
                    )

                elif role == "assistant":

                    messages.append(
                        ("assistant", content)
                    )

        messages.append(
            ("human", message)
        )

        # ---------------------------------------------------------
        # Execute agent
        # ---------------------------------------------------------

        try:

            result = await agent.ainvoke(
                {
                    "messages": messages
                },
                config={
                    "recursion_limit": 8
                },
            )

        except Exception as exc:

            logger.exception(
                "Agent execution failed"
            )

            return {
                "answer": (
                    "Une erreur est survenue lors du traitement "
                    "de votre demande."
                ),
                "tools_used": [],
            }

        # ---------------------------------------------------------
        # Result messages
        # ---------------------------------------------------------

        result_messages = result.get(
            "messages",
            []
        )

        logger.info(
            "===== AGENT FINISHED ====="
        )

        logger.info(
            "Number of messages: %s",
            len(result_messages)
        )

        # ---------------------------------------------------------
        # Tools used
        # ---------------------------------------------------------

        tools_used: list[str] = []

        if preloaded_context:
            tools_used.append(
                "search_documents"
            )

        for msg in result_messages:

            tool_calls = getattr(
                msg,
                "tool_calls",
                None,
            )

            if not tool_calls:
                continue

            for tool_call in tool_calls:

                tool_name = tool_call.get(
                    "name"
                )

                if (
                    tool_name
                    and tool_name not in tools_used
                ):
                    tools_used.append(
                        tool_name
                    )

        # ---------------------------------------------------------
        # Extract final answer
        # ---------------------------------------------------------

        answer = ""

        for msg in reversed(result_messages):

            content = getattr(
                msg,
                "content",
                "",
            )

            if not isinstance(content, str):
                continue

            content = content.strip()

            if not content:
                continue

            if content.lower() in [
                "sorry, need more steps to process this request.",
                "sorry, need more steps to process this request",
            ]:
                continue

            # Ne pas retourner les erreurs internes MCP comme réponse
            # finale si l'agent a réussi à produire une réponse après.
            if content.startswith(
                "Error executing tool"
            ):
                continue

            answer = content
            break

        if answer:
            answer = remove_empty_bullet_lines(
                answer
            )

        # ---------------------------------------------------------
        # Fallback
        # ---------------------------------------------------------

        if (
            preloaded_context
            and (
                not answer
                or is_document_fallback_answer(
                    answer
                )
                or (
                    should_use_extractive_grounding(
                        message
                    )
                    and (
                        not preloaded_args
                        or preloaded_args.get(
                            "category"
                        )
                        != "training"
                    )
                )
            )
        ):
            context_answer = build_answer_from_preloaded_context(
                preloaded_context,
                message,
            )

            if context_answer:
                if (
                    not answer
                    or is_document_fallback_answer(
                        answer
                    )
                ):
                    logger.warning(
                        "Agent returned document fallback despite preloaded RAG context; using top grounded result"
                    )
                answer = context_answer

        if not answer:

            answer = DOCUMENT_FALLBACK_ANSWER

        # ---------------------------------------------------------
        # Logs
        # ---------------------------------------------------------

        logger.info(
            "TOOLS USED: %s",
            tools_used,
        )

        # ---------------------------------------------------------
        # Response
        # ---------------------------------------------------------

        return {
            "answer": answer,
            "tools_used": tools_used,
        }


# IMPORTANT :
# Instance globale utilisée par les routes.

chat_service = ChatService()
