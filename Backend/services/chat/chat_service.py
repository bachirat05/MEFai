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
from services.chat.prompt import SYSTEM_PROMPT
from services.chat.model_factory import build_model
from services.chat.question_analyzer import (is_document_question, extract_search_subject, infer_document_category)
from services.chat.conversation_context import build_contextual_search_query
from services.chat.document_context import preload_document_context
from services.chat.answer_utils import (
    DOCUMENT_FALLBACK_ANSWER,
    build_answer_from_preloaded_context,
    is_document_fallback_answer,
    remove_empty_bullet_lines,
    should_use_extractive_grounding,
)

logger = logging.getLogger(__name__)

class ChatService:

    def __init__(self) -> None:
        self.model: ChatOllama | None = None
        self.settings = get_settings()

    def _get_model(self) -> ChatOllama:

        if self.model is None:
            self.model = build_model()

        return self.model

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
            await preload_document_context(
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