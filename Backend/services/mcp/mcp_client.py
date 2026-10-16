# Bloc des importations
from __future__ import annotations
import logging
import unicodedata
from contextlib import AsyncExitStack
from typing import Any, Optional

from langchain_core.tools import StructuredTool
from mcp import ClientSession
from mcp.client.sse import sse_client
from pydantic import create_model, Field


logger = logging.getLogger(__name__)

# fonction pour normaliser un texte en supprimant les accents et en convertissant les lettres en minuscules
def normalize_intent_text(value: str) -> str:
    return (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )


# fonction pour détecter si un texte correspond à une question sur la procédure liée à une formation ou à une certification
def is_training_procedure_intent(value: str) -> bool:
    normalized = normalize_intent_text(value)

    training_markers = (
        "formation",
        "certification",
        "certificat",
        "certif",
    )
    procedure_markers = (
        "delai",
        "preavis",
        "quand",
        "combien de jours",
        "combien de temps",
        "a l'avance",
        "avance",
        "soumettre",
        "envoyer",
        "demande",
        "inscription",
        "procedure",
        "validation",
        "valider",
        "responsable",
        "qui",
        "intervient",
        "etape",
    )

    return (
        any(marker in normalized for marker in training_markers)
        and any(marker in normalized for marker in procedure_markers)
    )


# fonction pour préparer et corrige les paramètres utilisés pour rechercher des documents ; une bonne requête, une catégorie adaptée et des paramètres de recherche valides
def normalize_search_documents_arguments(
    arguments: dict[str, Any],
    original_message: str | None = None,
) -> dict[str, Any]:
    normalized = dict(arguments)
    query = str(normalized.get("query") or "")
    intent_source = " ".join(
        part
        for part in (
            original_message,
            query,
        )
        if part
    )

    general_hr_search_markers = (
        "documents disponibles",
        "documents rh",
        "ressources humaines",
        "recherche generale",
        "recherche générale",
        "rechercher les documents",
        "liste des documents",
    )
    normalized_query = normalize_intent_text(query)
    is_general_hr_search = any(
        normalize_intent_text(marker) in normalized_query
        for marker in general_hr_search_markers
    )

    if (
        is_general_hr_search
        and normalized.get("category") == "other"
    ):
        normalized["category"] = None

    if normalized.get("category") in {
        "other",
        "general",
        "unknown",
        "",
    }:
        normalized["category"] = None

    if original_message:
        original_tokens = set(
            normalize_intent_text(original_message).split()
        )
        query_tokens = set(
            normalize_intent_text(query).split()
        )
        meaningful_original_tokens = {
            token
            for token in original_tokens
            if len(token) >= 4
        }
        overlap = meaningful_original_tokens & query_tokens

        if (
            meaningful_original_tokens
            and len(overlap) < max(
                1,
                len(meaningful_original_tokens) // 3,
            )
        ):
            normalized["query"] = original_message
            query = original_message

    if is_training_procedure_intent(intent_source):
        normalized["category"] = "training"

        if original_message and (
            not query
            or not is_training_procedure_intent(query)
        ):
            normalized["query"] = original_message

        try:
            normalized["top_k"] = max(
                int(normalized.get("top_k") or 5),
                8,
            )
        except (TypeError, ValueError):
            normalized["top_k"] = 8

        try:
            threshold = float(
                normalized.get("similarity_threshold", 0.5)
            )
        except (TypeError, ValueError):
            threshold = 0.5

        normalized["similarity_threshold"] = min(
            max(threshold, 0.0),
            0.5,
        )

    try:
        normalized["top_k"] = max(
            int(normalized.get("top_k") or 8),
            8,
        )
    except (TypeError, ValueError):
        normalized["top_k"] = 8

    try:
        threshold = float(
            normalized.get("similarity_threshold", 0.35)
        )
    except (TypeError, ValueError):
        threshold = 0.35

    normalized["similarity_threshold"] = min(
        max(threshold, 0.0),
        0.5,
    )

    return normalized


class MCPClient:

    def __init__(
        self,
        server_url: str = "http://127.0.0.1:8000/mcp/sse",
    ) -> None:
        self.server_url = server_url

    # =========================================================
    # Extract MCP input schema

    # Cette méthode reçoit un outil MCP découvert sur le serveur et tente de récupérer son schéma d'entrée.
    # Un schéma d'entrée décrit les paramètres qu'un outil accepte : leur nom, leur type et parfois leur caractère obligatoire.
    def _get_input_schema(
        self,
        mcp_tool: Any,
    ) -> dict[str, Any] | None:

        # -----------------------------------------------------
        # 1. Standard MCP Python SDK attribute
        # -----------------------------------------------------

        schema = getattr(
            mcp_tool,
            "inputSchema",
            None,
        )

        if isinstance(schema, dict):
            return schema

        # -----------------------------------------------------
        # 2. Alternative snake_case attribute
        # -----------------------------------------------------

        schema = getattr(
            mcp_tool,
            "input_schema",
            None,
        )

        if isinstance(schema, dict):
            return schema

        # -----------------------------------------------------
        # 3. Pydantic model dump
        # -----------------------------------------------------

        try:
            if hasattr(mcp_tool, "model_dump"):

                data = mcp_tool.model_dump(
                    by_alias=True
                )

                if isinstance(data, dict):

                    schema = data.get(
                        "inputSchema"
                    )

                    if isinstance(schema, dict):
                        return schema

                    schema = data.get(
                        "input_schema"
                    )

                    if isinstance(schema, dict):
                        return schema

        except Exception as exc:

            logger.warning(
                "Could not extract schema with model_dump: %s",
                exc,
            )

        # -----------------------------------------------------
        # 4. __dict__ fallback
        # -----------------------------------------------------

        try:

            data = vars(mcp_tool)

            schema = data.get(
                "inputSchema"
            )

            if isinstance(schema, dict):
                return schema

            schema = data.get(
                "input_schema"
            )

            if isinstance(schema, dict):
                return schema

        except Exception:
            pass

        return None


    # =========================================================
    # Convert JSON schema -> Pydantic model
    # cette méthode sert à transformer le schéma JSON d'un outil MCP en un modèle Pydantic que LangChain pourra utiliser
    def _build_args_schema(
        self,
        tool_name: str,
        input_schema: dict[str, Any] | None,
    ):

        if not input_schema:
            logger.warning(
                "No input schema found for MCP tool '%s'",
                tool_name,
            )
            return None

        properties = input_schema.get(
            "properties",
            {},
        )

        required = set(
            input_schema.get(
                "required",
                [],
            )
        )

        if not isinstance(properties, dict):
            return None

        fields: dict[str, Any] = {}

        for field_name, field_info in properties.items():

            if not isinstance(
                field_info,
                dict,
            ):
                field_info = {}

            json_type = field_info.get(
                "type"
            )

            description = field_info.get(
                "description",
                "",
            )

            # -------------------------------------------------
            # JSON Schema -> Python
            # -------------------------------------------------

            if json_type == "string":
                python_type = str

            elif json_type == "integer":
                python_type = int

            elif json_type == "number":
                python_type = float

            elif json_type == "boolean":
                python_type = bool

            elif json_type == "array":
                python_type = list[Any]

            elif json_type == "object":
                python_type = dict[str, Any]

            else:
                python_type = Any

            # -------------------------------------------------
            # Required / Optional
            # -------------------------------------------------

            if field_name in required:

                fields[field_name] = (
                    python_type,
                    Field(
                        ...,
                        description=description,
                    ),
                )

            else:

                fields[field_name] = (
                    Optional[python_type],
                    Field(
                        default=None,
                        description=description,
                    ),
                )

        if not fields:
            return None

        # -----------------------------------------------------
        # Create dynamic Pydantic model
        # -----------------------------------------------------

        model_name = (
            f"{tool_name.replace('-', '_')}Arguments"
        )

        args_schema = create_model(
            model_name,
            **fields,
        )

        return args_schema


    # =========================================================
    # Get MCP tools

    async def get_tools(
        self,
        stack: AsyncExitStack,
        authenticated_user: dict[str, Any] | None = None,
    ) -> list[StructuredTool]:

        # -----------------------------------------------------
        # Connect to MCP SSE
        # -----------------------------------------------------

        read_stream, write_stream = (
            await stack.enter_async_context(
                sse_client(
                    self.server_url
                )
            )
        )

        session = await stack.enter_async_context(
            ClientSession(
                read_stream,
                write_stream,
            )
        )

        await session.initialize()

        logger.info(
            "MCP session initialized"
        )

        # -----------------------------------------------------
        # Discover tools
        # -----------------------------------------------------

        response = await session.list_tools()

        tools: list[StructuredTool] = []

        # -----------------------------------------------------
        # Convert MCP tools
        # -----------------------------------------------------

        for mcp_tool in response.tools:

            tool_name = mcp_tool.name

            tool_description = (
                mcp_tool.description
                or f"MCP tool: {tool_name}"
            )

            # =================================================
            # Get schema
            # =================================================

            input_schema = self._get_input_schema(
                mcp_tool
            )

            if (
                tool_name == "soumettre_demande_conge"
                and isinstance(input_schema, dict)
            ):
                input_schema = dict(input_schema)
                properties = dict(
                    input_schema.get(
                        "properties",
                        {},
                    )
                )
                for internal_field in (
                    "user_uid",
                    "employee_email",
                    "user_role",
                ):
                    properties.pop(
                        internal_field,
                        None,
                    )
                input_schema["properties"] = properties
                input_schema["required"] = [
                    field
                    for field in input_schema.get(
                        "required",
                        [],
                    )
                    if field not in {
                        "user_uid",
                        "employee_email",
                        "user_role",
                    }
                ]

            logger.info(
                "MCP tool discovered: %s | schema=%r",
                tool_name,
                input_schema,
            )

            # =================================================
            # Build Pydantic args schema
            # =================================================

            args_schema = self._build_args_schema(
                tool_name,
                input_schema,
            )

            logger.info(
                "MCP tool schema generated: %s | %s",
                tool_name,
                args_schema,
            )

            # =================================================
            # Create MCP caller
            # =================================================

            async def call_tool(
                _tool_name: str = tool_name,
                **kwargs: Any,
            ) -> str:

                logger.info(
                    "Calling MCP tool '%s' with arguments: %s",
                    _tool_name,
                    kwargs,
                )

                # -------------------------------------------------
                # Normalize search_documents arguments
                # -------------------------------------------------
                if _tool_name == "search_documents":
                    query = str(kwargs.get("query", "")
                        ).lower()
                    general_hr_search_markers = (
                        "documents disponibles",
                        "documents rh",
                        "ressources humaines",
                        "recherche générale",
                        "rechercher les documents",
                        "liste des documents",
                    )
                    is_general_hr_search = any(
                        marker in query
                        for marker in general_hr_search_markers
                    )

                    if (
                        is_general_hr_search
                        and kwargs.get("category") == "other"
                    ):
                        logger.info(
                            "General RH search detected — "
                            "forcing category=None instead of 'other'"
                        )
                        kwargs["category"] = None

                        # -------------------------------------------------
                        # Remove None values
                        # -------------------------------------------------

                        
                if _tool_name == "search_documents":
                    before_final_normalization = dict(kwargs)
                    kwargs = normalize_search_documents_arguments(
                        kwargs
                    )
                    logger.info(
                        "search_documents final args | before=%s | after=%s",
                        before_final_normalization,
                        kwargs,
                    )

                clean_kwargs = {
                    key : value
                    for key, value in kwargs.items()
                    if value is not None
                }

                clean_kwargs.pop(
                    "manager_email",
                    None,
                )

                if (
                    _tool_name == "soumettre_demande_conge"
                    and authenticated_user is not None
                ):
                    clean_kwargs.update(
                        {
                            "user_uid": authenticated_user.get(
                                "uid",
                                "",
                            ),
                            "employee_email": authenticated_user.get(
                                "email",
                                "",
                            ),
                            "user_role": authenticated_user.get(
                                "role",
                                "",
                            ),
                        }
                    )

                logger.info(
                    "MCP clean arguments '%s': %s",
                    _tool_name,
                    clean_kwargs,
                )

                # -------------------------------------------------
                # Call MCP server
                # -------------------------------------------------

                result = await session.call_tool(
                    _tool_name,
                    arguments=clean_kwargs,
                )

                # -------------------------------------------------
                # Extract text
                # -------------------------------------------------

                if hasattr(
                    result,
                    "content",
                ):

                    parts: list[str] = []

                    for item in result.content:

                        text = getattr(
                            item,
                            "text",
                            None,
                        )

                        if text:
                            parts.append(
                                text
                            )

                    return "\n".join(parts)

                return str(result)

            # =================================================
            # Create LangChain StructuredTool
            # =================================================

            if args_schema is not None:

                tool = StructuredTool.from_function(
                    coroutine=call_tool,
                    name=tool_name,
                    description=tool_description,
                    args_schema=args_schema,
                )

            else:

                tool = StructuredTool.from_function(
                    coroutine=call_tool,
                    name=tool_name,
                    description=tool_description,
                )

            tools.append(tool)

            logger.info(
                "MCP tool registered: %s | schema=%s",
                tool_name,
                tool.args_schema,
            )

        # -----------------------------------------------------
        # Final
        # -----------------------------------------------------

        logger.info(
            "MCP tools discovered: %s",
            [
                tool.name
                for tool in tools
            ],
        )

        return tools
