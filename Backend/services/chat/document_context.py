# Fichier pour orchestrer l'appel à la recherche documentaire 
""" ce fichier permet de : 
        1. Vérifie que la question concerne les documents RH.
        2. Recherche l'outil MCP nommé search_documents.
        3. Détermine la catégorie et construit la requête de recherche.
        4. Prépare les paramètres, notamment top_k=8 et le seuil de similarité.
        5. Appelle l'outil avec await search_tool.ainvoke(search_args).
        6. Retourne le contexte récupéré et les arguments de recherche.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from langchain_core.tools import StructuredTool

from Backend.services.mcp.mcp_client import (
    normalize_search_documents_arguments,
)

from chat.question_analyzer import (is_document_question, infer_document_category)
from chat.conversation_context import build_contextual_search_query

logger = logging.getLogger(__name__)

def find_search_documents_tool(
        self,
        tools: list[StructuredTool],
    ) -> StructuredTool | None:
        for tool in tools:
            if tool.name == "search_documents":
                return tool

        return None

async def preload_document_context(
        self,
        message: str,
        tools: list[StructuredTool],
        history: list[dict[str, str]] | None = None,
    ) -> tuple[str | None, dict[str, Any] | None]:
        if not is_document_question(
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

        category = infer_document_category(
            message
        )
        search_query = build_contextual_search_query(
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
