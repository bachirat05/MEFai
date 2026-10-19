from __future__ import annotations

from schemas.document import DocumentSearchQuery
from services.rag.retriever import Retriever

PROMPT = """Tu es un assistant RH. Réponds uniquement à partir du contexte ci-dessous.
Si l'information n'y est pas, dis-le clairement.

Contexte :
{context}

Question : {question}
Réponse :"""


class RAGChain:
    def __init__(self, retriever: Retriever, llm) -> None:
        self._retriever = retriever
        self._llm = llm

    def answer(self, question: str, top_k: int = 5) -> dict:
        response = self._retriever.search(
            DocumentSearchQuery(query=question, top_k=top_k)
        )
        context = "\n\n---\n\n".join(r.content for r in response.results)
        reply = self._llm.invoke(PROMPT.format(context=context, question=question))
        return {
            "answer": getattr(reply, "content", reply),
            "sources": [r.metadata.filename for r in response.results],
        }