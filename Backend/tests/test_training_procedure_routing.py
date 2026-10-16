from __future__ import annotations

import pytest

import app.main as main_module
import services.chat.chat_service as chat_service_module

from schemas.document import (
    DocumentCategory,
    DocumentMetadata,
    DocumentSearchResponse,
    DocumentSearchResult,
    DocumentSource,
)
from services.chat.chat_service import ChatService
from services.chat.chat_service import (
    build_answer_from_preloaded_context,
    remove_empty_bullet_lines,
)
from Backend.services.mcp.mcp_client import normalize_search_documents_arguments


class FakeRAGService:
    is_initialized = True

    def __init__(self) -> None:
        self.categories: list[DocumentCategory | None] = []
        self.queries: list[str] = []

    def search(self, query) -> DocumentSearchResponse:
        self.categories.append(query.category)
        self.queries.append(query.query)

        return DocumentSearchResponse(
            query=query.query,
            results=[
                DocumentSearchResult(
                    document_id="formation-process",
                    content=(
                        "Etape: 1\n"
                        "Responsable: Employe\n"
                        "Delai cible: Au moins 10 jours ouvres avant la session\n"
                        "Action: Soumettre une demande.\n\n"
                        "Etape: 2\n"
                        "Responsable: Manager\n"
                        "Delai cible: Sous 3 jours ouvres\n"
                        "Action: Valider ou refuser.\n\n"
                        "Etape: 3\n"
                        "Responsable: RH / Administration\n"
                        "Delai cible: Sous 5 jours ouvres apres validation manager\n"
                        "Action: Verifier l'eligibilite."
                    ),
                    metadata=DocumentMetadata(
                        category=DocumentCategory.TRAINING,
                        source=DocumentSource.INTERNAL_WIKI,
                        department="RH",
                        tags=[
                            "formation",
                            "processus",
                        ],
                    ),
                    score=0.9,
                )
            ],
            total_found=1,
            returned_count=1,
        )


class FallbackRAGService(FakeRAGService):
    def search(self, query) -> DocumentSearchResponse:
        if query.category == DocumentCategory.HR_PROCEDURE:
            self.categories.append(query.category)
            self.queries.append(query.query)

            return DocumentSearchResponse(
                query=query.query,
                results=[],
                total_found=0,
                returned_count=0,
            )

        return super().search(query)


class TrainingProcessRAGService:
    is_initialized = True

    def search(self, query) -> DocumentSearchResponse:
        return DocumentSearchResponse(
            query=query.query,
            results=[
                DocumentSearchResult(
                    document_id="training-example",
                    content=(
                        "Situation: Employe ayant reussi une certification de 3 000 MAD\n"
                        "Decision selon cette politique de demonstration: Remboursement maximal."
                    ),
                    metadata=DocumentMetadata(
                        category=DocumentCategory.TRAINING,
                        source=DocumentSource.INTERNAL_WIKI,
                        department="RH",
                        tags=[
                            "formation",
                        ],
                    ),
                    score=0.99,
                ),
                DocumentSearchResult(
                    document_id="training-process",
                    content=(
                        "Etape: 1\n"
                        "Responsable: Employe\n"
                        "Delai cible: Au moins 10 jours ouvres avant la session\n"
                        "Action: Soumettre une demande avec intitule, organisme, dates, cout estime et objectif professionnel.\n\n"
                        "Etape: 2\n"
                        "Responsable: Manager\n"
                        "Delai cible: Sous 3 jours ouvres\n"
                        "Action: Valider ou refuser."
                    ),
                    metadata=DocumentMetadata(
                        category=DocumentCategory.TRAINING,
                        source=DocumentSource.INTERNAL_WIKI,
                        department="RH",
                        tags=[
                            "formation",
                            "processus",
                        ],
                    ),
                    score=0.55,
                ),
            ],
            total_found=2,
            returned_count=2,
        )


class CategoryFallbackRAGService:
    is_initialized = True

    def __init__(self) -> None:
        self.categories: list[DocumentCategory | None] = []

    def search(self, query) -> DocumentSearchResponse:
        self.categories.append(
            query.category
        )

        if query.category is not None:
            return DocumentSearchResponse(
                query=query.query,
                results=[],
                total_found=0,
                returned_count=0,
            )

        return DocumentSearchResponse(
            query=query.query,
            results=[
                DocumentSearchResult(
                    document_id="dynamic-mobility",
                    content=(
                        "Le delai de traitement d'une demande de mobilite "
                        "interne est de 17 jours ouvres. "
                        "Le code de reference est MOB-TEST-917."
                    ),
                    metadata=DocumentMetadata(
                        category=DocumentCategory.OTHER,
                        source=DocumentSource.INTERNAL_WIKI,
                        department="RH",
                        tags=[
                            "mobilite_interne.txt",
                        ],
                        filename="mobilite_interne.txt",
                        document_type="txt",
                        chunk_index=1,
                        chunk_count=1,
                    ),
                    score=0.81,
                )
            ],
            total_found=1,
            returned_count=1,
        )


class EquipmentRerankRAGService:
    is_initialized = True

    def search(self, query) -> DocumentSearchResponse:
        return DocumentSearchResponse(
            query=query.query,
            results=[
                DocumentSearchResult(
                    document_id="training-amount",
                    content=(
                        "Frais d'examen | Remboursement a hauteur de 80 % "
                        "apres reussite | 2 500 MAD par certification"
                    ),
                    metadata=DocumentMetadata(
                        category=DocumentCategory.TRAINING,
                        source=DocumentSource.INTERNAL_WIKI,
                        department="RH",
                        tags=["formation"],
                        filename="formation.txt",
                    ),
                    score=0.91,
                ),
                DocumentSearchResult(
                    document_id="equipment-policy",
                    content=(
                        "POLITIQUE MATERIEL TEST\n"
                        "Renouvellement: tous les 7 ans.\n"
                        "Plafond accessoires: 875 MAD.\n"
                        "En cas de panne informatique, signaler au support "
                        "dans un delai maximum de 24 heures.\n"
                        "Code: MAT-RAG-731."
                    ),
                    metadata=DocumentMetadata(
                        category=DocumentCategory.RH_POLICY,
                        source=DocumentSource.INTERNAL_WIKI,
                        department="RH",
                        tags=[
                            "politique_materiel_test.txt",
                            "materiel",
                        ],
                        filename="politique_materiel_test.txt",
                        document_type="txt",
                        chunk_index=1,
                        chunk_count=1,
                    ),
                    score=0.52,
                ),
            ],
            total_found=2,
            returned_count=2,
        )


def test_training_procedure_category_is_normalized_to_training() -> None:
    assert (
        main_module.normalize_document_search_category(
            "Qui valide une demande de formation apres l'employe ?",
            "hr_procedure",
        )
        == "training"
    )


@pytest.mark.asyncio
async def test_search_documents_finds_training_responsible_when_agent_uses_hr_procedure() -> None:
    fake_rag = FakeRAGService()
    previous_rag = main_module.rag_service
    main_module.rag_service = fake_rag

    try:
        result = await main_module.search_documents(
            query="Qui valide une demande de formation apres l'employe ?",
            category="hr_procedure",
            top_k=5,
            similarity_threshold=0.5,
        )
    finally:
        main_module.rag_service = previous_rag

    assert fake_rag.categories == [
        DocumentCategory.TRAINING
    ]
    assert "Responsable: Manager" in result
    assert "Sous 3 jours ouvres" in result
    assert "Responsable: RH / Administration" in result


@pytest.mark.asyncio
async def test_search_documents_falls_back_to_training_when_hr_procedure_is_empty() -> None:
    fake_rag = FallbackRAGService()
    previous_rag = main_module.rag_service
    main_module.rag_service = fake_rag

    try:
        result = await main_module.search_documents(
            query="Combien de temps le manager a-t-il pour valider une demande ?",
            category="hr_procedure",
            top_k=5,
            similarity_threshold=0.5,
        )
    finally:
        main_module.rag_service = previous_rag

    assert fake_rag.categories[:2] == [
        DocumentCategory.HR_PROCEDURE,
        DocumentCategory.TRAINING,
    ]
    assert "Responsable: Manager" in result
    assert "Sous 3 jours ouvres" in result


@pytest.mark.asyncio
async def test_search_documents_falls_back_to_global_search_for_wrong_category() -> None:
    fake_rag = CategoryFallbackRAGService()
    previous_rag = main_module.rag_service
    main_module.rag_service = fake_rag

    try:
        result = await main_module.search_documents(
            query="Combien de temps prend une demande de mobilite interne ?",
            category="benefits",
            top_k=8,
            similarity_threshold=0.35,
        )
    finally:
        main_module.rag_service = previous_rag

    assert fake_rag.categories == [
        DocumentCategory.BENEFITS,
        None,
    ]
    assert "17 jours ouvres" in result
    assert "MOB-TEST-917" in result
    assert "mobilite_interne.txt" in result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("question", "expected"),
    [
        (
            "Quel est le montant maximal remboursable pour un accessoire professionnel ?",
            "875 MAD",
        ),
        (
            "Tous les combien d'annees un ordinateur professionnel est-il renouvele ?",
            "7 ans",
        ),
        (
            "Dans quel delai faut-il signaler une panne informatique ?",
            "24 heures",
        ),
        (
            "Quel est le code de reference de la politique materiel ?",
            "MAT-RAG-731",
        ),
    ],
)
async def test_search_documents_reranks_hardware_policy_values(
    question: str,
    expected: str,
) -> None:
    fake_rag = EquipmentRerankRAGService()
    previous_rag = main_module.rag_service
    main_module.rag_service = fake_rag

    try:
        result = await main_module.search_documents(
            query=question,
            category=None,
            top_k=10,
            similarity_threshold=0.35,
        )
    finally:
        main_module.rag_service = previous_rag

    first_result = result.split(
        "--- Résultat 2"
    )[0]

    assert expected in first_result
    assert "politique_materiel_test.txt" in first_result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query",
    [
        "Quel est le delai minimum pour soumettre une demande de formation ?",
        "Combien de jours avant une formation dois-je envoyer ma demande ?",
        "Quand dois-je soumettre ma demande de formation ?",
        "Quel preavis faut-il respecter pour une formation ?",
    ],
)
async def test_training_submission_delay_queries_prioritize_process_chunk(
    query: str,
) -> None:
    fake_rag = TrainingProcessRAGService()
    previous_rag = main_module.rag_service
    main_module.rag_service = fake_rag

    try:
        result = await main_module.search_documents(
            query=query,
            category="training",
            top_k=5,
            similarity_threshold=0.5,
        )
    finally:
        main_module.rag_service = previous_rag

    first_result = result.split(
        "--- Résultat 2"
    )[0]

    assert "Delai cible: Au moins 10 jours ouvres avant la session" in first_result
    assert "Action: Soumettre une demande" in first_result


def test_mcp_normalization_preserves_original_training_procedure_query() -> None:
    args = normalize_search_documents_arguments(
        {
            "query": "regles formation",
            "category": "other",
            "top_k": 3,
            "similarity_threshold": 0.82,
        },
        original_message=(
            "Quel preavis faut-il respecter pour une formation ?"
        ),
    )

    assert args == {
        "query": "Quel preavis faut-il respecter pour une formation ?",
        "category": "training",
        "top_k": 8,
        "similarity_threshold": 0.5,
    }


class FakeAgentMessage:
    def __init__(
        self,
        content: str,
        tool_calls=None,
    ) -> None:
        self.content = content
        self.tool_calls = tool_calls


class FakeAgent:
    def __init__(
        self,
        captured_payloads: list[dict],
    ) -> None:
        self.captured_payloads = captured_payloads

    async def ainvoke(
        self,
        payload,
        config=None,
    ):
        self.captured_payloads.append(
            payload
        )

        system_context = "\n".join(
            content
            for role, content in payload["messages"]
            if role == "system"
        )

        assert "search_documents" in system_context
        assert "Delai cible: Au moins 10 jours ouvres avant la session" in system_context
        assert "Action: Soumettre une demande" in system_context

        return {
            "messages": [
                FakeAgentMessage(
                    (
                        "Au moins 10 jours ouvres avant la session. "
                        "[Source: Documentation RH interne | Category: Formation]"
                    )
                )
            ]
        }


class FakeSearchDocumentsTool:
    name = "search_documents"

    def __init__(
        self,
        calls: list[dict],
    ) -> None:
        self.calls = calls

    async def ainvoke(
        self,
        kwargs: dict,
    ) -> str:
        self.calls.append(
            kwargs
        )

        return (
            "Resultats pour la formation:\n"
            "--- Resultat 1 ---\n"
            "Etape: 1\n"
            "Responsable: Employe\n"
            "Delai cible: Au moins 10 jours ouvres avant la session\n"
            "Action: Soumettre une demande.\n"
            "--- Resultat 2 ---\n"
            "Etape: 2\n"
            "Responsable: Manager\n"
            "Delai cible: Sous 3 jours ouvres\n"
            "Action: Valider ou refuser.\n"
            "--- Resultat 3 ---\n"
            "Responsable: RH / Administration"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "question",
    [
        "Qui valide une demande de formation apres l'employe ?",
        "Combien de temps le manager a-t-il pour valider une demande de formation ?",
        "Quel est le delai minimum pour soumettre une demande de formation ?",
        "Combien de jours avant une formation dois-je envoyer ma demande ?",
        "Quand dois-je soumettre ma demande de formation ?",
        "Quel preavis faut-il respecter pour une formation ?",
        "A quel moment faut-il envoyer une demande de formation ?",
        "Combien de temps a l'avance dois-je demander une formation ?",
    ],
)
async def test_chat_service_preloads_training_procedure_context(
    monkeypatch: pytest.MonkeyPatch,
    question: str,
) -> None:
    search_calls: list[dict] = []
    captured_payloads: list[dict] = []

    def fake_create_react_agent(
        model,
        tools,
    ):
        return FakeAgent(
            captured_payloads
        )

    monkeypatch.setattr(
        chat_service_module,
        "create_react_agent",
        fake_create_react_agent,
    )
    monkeypatch.setattr(
        ChatService,
        "_get_model",
        lambda self: object(),
    )

    result = await ChatService().run_agent(
        message=question,
        tools=[
            FakeSearchDocumentsTool(
                search_calls
            )
        ],
        history=[],
    )

    assert search_calls == [
        {
            "query": question,
            "category": "training",
            "top_k": 8,
            "similarity_threshold": 0.5,
        }
    ]
    assert captured_payloads
    assert result["tools_used"] == [
        "search_documents"
    ]
    assert "10 jours ouvres" in result["answer"]


@pytest.mark.asyncio
async def test_chat_service_preloads_generic_document_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    question = "Combien de temps prend une demande de mobilite interne ?"
    search_calls: list[dict] = []
    captured_payloads: list[dict] = []

    class GenericFakeAgent(FakeAgent):
        async def ainvoke(
            self,
            payload,
            config=None,
        ):
            self.captured_payloads.append(
                payload
            )
            system_context = "\n".join(
                content
                for role, content in payload["messages"]
                if role == "system"
            )

            assert "17 jours ouvres" in system_context
            assert "MOB-TEST-917" in system_context

            return {
                "messages": [
                    FakeAgentMessage(
                        (
                            "La demande de mobilite interne prend "
                            "17 jours ouvres. "
                            "[Source: Documentation RH interne | Category: Autre]"
                        )
                    )
                ]
            }

    class GenericSearchDocumentsTool(FakeSearchDocumentsTool):
        async def ainvoke(
            self,
            kwargs: dict,
        ) -> str:
            self.calls.append(
                kwargs
            )

            return (
                "Resultats pour la mobilite interne:\n"
                "--- Resultat 1 ---\n"
                "Le delai de traitement d'une demande de mobilite "
                "interne est de 17 jours ouvres.\n"
                "Le code de reference est MOB-TEST-917."
            )

    def fake_create_react_agent(
        model,
        tools,
    ):
        return GenericFakeAgent(
            captured_payloads
        )

    monkeypatch.setattr(
        chat_service_module,
        "create_react_agent",
        fake_create_react_agent,
    )
    monkeypatch.setattr(
        ChatService,
        "_get_model",
        lambda self: object(),
    )

    result = await ChatService().run_agent(
        message=question,
        tools=[
            GenericSearchDocumentsTool(
                search_calls
            )
        ],
        history=[],
    )

    assert search_calls == [
        {
            "query": question,
            "category": None,
            "top_k": 8,
            "similarity_threshold": 0.35,
        }
    ]
    assert captured_payloads
    assert result["tools_used"] == [
        "search_documents"
    ]
    assert "17 jours ouvres" in result["answer"]


@pytest.mark.asyncio
async def test_chat_service_uses_preloaded_context_when_agent_returns_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    question = "Quel est le delai de traitement d'une demande de mobilite interne ?"
    search_calls: list[dict] = []

    class FallbackAgent:
        async def ainvoke(
            self,
            payload,
            config=None,
        ):
            return {
                "messages": [
                    FakeAgentMessage(
                        "Les documents internes actuels ne précisent pas cette information."
                    )
                ]
            }

    class MobilitySearchDocumentsTool(FakeSearchDocumentsTool):
        async def ainvoke(
            self,
            kwargs: dict,
        ) -> str:
            self.calls.append(
                kwargs
            )

            return (
                "Resultats pour la mobilite interne:\n\n"
                "--- Résultat 1 (score: 0.7000) ---\n"
                "[Source: Documentation RH interne | Category: Politique RH | File: fich2.txt]\n"
                "Le delai de traitement d'une demande de mobilite interne "
                "est de 17 jours ouvres.\n\n"
                "--- Résultat 2 (score: 0.4000) ---\n"
                "Autre contenu."
            )

    monkeypatch.setattr(
        chat_service_module,
        "create_react_agent",
        lambda model, tools: FallbackAgent(),
    )
    monkeypatch.setattr(
        ChatService,
        "_get_model",
        lambda self: object(),
    )

    result = await ChatService().run_agent(
        message=question,
        tools=[
            MobilitySearchDocumentsTool(
                search_calls
            )
        ],
        history=[],
    )

    assert search_calls
    assert "17 jours ouvres" in result["answer"]
    assert "fich2.txt" in result["answer"]


def test_build_answer_from_preloaded_context_extracts_top_result() -> None:
    answer = build_answer_from_preloaded_context(
        (
            "Résultats pour 'question':\n\n"
            "--- Résultat 1 (score: 0.7000) ---\n"
            "[Source: Documentation RH interne | Category: Autre]\n"
            "La reponse documentaire prioritaire est presente.\n\n"
            "--- Résultat 2 (score: 0.6000) ---\n"
            "Autre resultat."
        )
    )

    assert answer is not None
    assert "La reponse documentaire prioritaire est presente." in answer
    assert "Autre resultat" not in answer


@pytest.mark.asyncio
async def test_chat_service_expands_follow_up_query_with_recent_document_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    question = "Quel est le code de reference de cette politique ?"
    search_calls: list[dict] = []

    class GenericAgent:
        async def ainvoke(
            self,
            payload,
            config=None,
        ):
            return {
                "messages": [
                    FakeAgentMessage(
                        (
                            "Le code de reference est XYZ-DEMO-481. "
                            "[Source: Documentation RH interne | Category: Autre]"
                        )
                    )
                ]
            }

    class FollowUpSearchDocumentsTool(FakeSearchDocumentsTool):
        async def ainvoke(
            self,
            kwargs: dict,
        ) -> str:
            self.calls.append(
                kwargs
            )

            return (
                "Resultats pour la mobilite interne:\n\n"
                "--- Résultat 1 (score: 0.7000) ---\n"
                "[Source: Documentation RH interne | Category: Autre | File: demo.txt]\n"
                "Le code de reference est XYZ-DEMO-481.\n"
                "Une indemnite de mobilite de 1 725 MAD est prevue."
            )

    monkeypatch.setattr(
        chat_service_module,
        "create_react_agent",
        lambda model, tools: GenericAgent(),
    )
    monkeypatch.setattr(
        ChatService,
        "_get_model",
        lambda self: object(),
    )

    result = await ChatService().run_agent(
        message=question,
        tools=[
            FollowUpSearchDocumentsTool(
                search_calls
            )
        ],
        history=[
            {
                "role": "user",
                "content": "Quelles sont les conditions de mobilite interne ?",
            },
            {
                "role": "assistant",
                "content": (
                    "La politique de mobilite interne precise plusieurs conditions. "
                    "[Source: Documentation RH interne | Category: Autre | File: demo.txt]"
                ),
            },
        ],
    )

    assert search_calls
    assert search_calls[0]["query"].startswith(
        question
    )
    assert search_calls[0]["category"] is None
    assert "mobilite interne" in search_calls[0]["query"]
    assert "demo.txt" in search_calls[0]["query"]
    assert "XYZ-DEMO-481" in result["answer"]


@pytest.mark.asyncio
async def test_chat_service_value_question_preloads_document_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    question = "Quel montant est prévu pour l'indemnité de mobilité ?"
    search_calls: list[dict] = []

    class ValueAgent:
        async def ainvoke(
            self,
            payload,
            config=None,
        ):
            return {
                "messages": [
                    FakeAgentMessage(
                        (
                            "Le montant prévu est 1 725 MAD. "
                            "[Source: Documentation RH interne | Category: Autre]"
                        )
                    )
                ]
            }

    class ValueSearchDocumentsTool(FakeSearchDocumentsTool):
        async def ainvoke(
            self,
            kwargs: dict,
        ) -> str:
            self.calls.append(
                kwargs
            )
            return (
                "--- Résultat 1 (score: 0.7000) ---\n"
                "[Source: Documentation RH interne | Category: Autre | File: demo.txt]\n"
                "Une indemnite de mobilite de 1 725 MAD est prevue."
            )

    monkeypatch.setattr(
        chat_service_module,
        "create_react_agent",
        lambda model, tools: ValueAgent(),
    )
    monkeypatch.setattr(
        ChatService,
        "_get_model",
        lambda self: object(),
    )

    result = await ChatService().run_agent(
        message=question,
        tools=[
            ValueSearchDocumentsTool(
                search_calls
            )
        ],
        history=[],
    )

    assert search_calls == [
        {
            "query": question,
            "category": None,
            "top_k": 8,
            "similarity_threshold": 0.35,
        }
    ]
    assert "1 725 MAD" in result["answer"]


def test_remove_empty_bullet_lines_removes_source_placeholders() -> None:
    answer = remove_empty_bullet_lines(
        (
            "Ce delai est mentionne explicitement dans plusieurs sources, notamment :\n"
            "-\n"
            "-\n"
            "\n"
            "La reponse utile reste presente."
        )
    )

    assert "\n-" not in answer
    assert "notamment" not in answer
    assert "La reponse utile reste presente." in answer


@pytest.mark.asyncio
async def test_chat_service_uses_extractive_grounding_for_action_questions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    question = "Que faut-il faire en cas de vol d'un ordinateur professionnel ?"
    search_calls: list[dict] = []

    class HallucinatingAgent:
        async def ainvoke(
            self,
            payload,
            config=None,
        ):
            return {
                "messages": [
                    FakeAgentMessage(
                        (
                            "Il faut informer le manager, le service informatique "
                            "et les autorites competentes."
                        )
                    )
                ]
            }

    class EquipmentSearchDocumentsTool(FakeSearchDocumentsTool):
        async def ainvoke(
            self,
            kwargs: dict,
        ) -> str:
            self.calls.append(
                kwargs
            )
            return (
                "Résultats pour la politique materiel:\n\n"
                "--- Résultat 1 (score: 0.7000) ---\n"
                "[Source: Documentation RH interne | Category: Politique RH | File: materiel.txt]\n"
                "6. Perte ou vol\n"
                "En cas de perte ou de vol d'un equipement professionnel, "
                "l'employe doit informer immediatement son manager et le "
                "service informatique.\n"
                "7. Code de reference\n"
                "Le code de reference est MAT-RAG-731."
            )

    monkeypatch.setattr(
        chat_service_module,
        "create_react_agent",
        lambda model, tools: HallucinatingAgent(),
    )
    monkeypatch.setattr(
        ChatService,
        "_get_model",
        lambda self: object(),
    )

    result = await ChatService().run_agent(
        message=question,
        tools=[
            EquipmentSearchDocumentsTool(
                search_calls
            )
        ],
        history=[],
    )

    assert search_calls
    assert "manager" in result["answer"]
    assert "service informatique" in result["answer"]
    assert "autorites competentes" not in result["answer"]
