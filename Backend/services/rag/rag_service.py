from __future__ import annotations

import hashlib
import logging

from langchain_chroma import Chroma
from langchain_core.documents import Document as LCDocument
from langchain_core.embeddings import Embeddings

from schemas.document import (
    DocumentCategory,
    DocumentIngestion,
    DocumentMetadata,
    DocumentSearchQuery,
    DocumentSearchResult,
    DocumentSource,
)

logger = logging.getLogger(__name__)

# Distance cosinus : similarity_search_with_score renvoie des distances dans [0, 2].
_COLLECTION_METADATA = {"hnsw:space": "cosine"}

# Nombre minimum de candidats remontés avant reranking.
CANDIDATE_POOL = 30


# Conversion Pydantic <-> dict stocké dans Chroma.
# Chroma n'accepte pas None : on stocke "" ou 0 et on restaure None à la lecture.


def _to_chroma(meta: DocumentMetadata, document_id: str) -> dict:
    return {
        "document_id": document_id,
        "category": meta.category.value,
        "source": meta.source.value,
        "department": meta.department,
        "tags": meta.tags,
        "filename": meta.filename or "",
        "document_type": meta.document_type or "",
        "chunk_index": meta.chunk_index or 0,
        "chunk_count": meta.chunk_count or 0,
        "effective_date": meta.effective_date or "",
        "author": meta.author or "",
        "version": meta.version,
    }


def _from_chroma(raw: dict) -> DocumentMetadata:
    return DocumentMetadata(
        category=DocumentCategory(raw.get("category", DocumentCategory.OTHER.value)),
        source=DocumentSource(raw.get("source", DocumentSource.MANUAL.value)),
        department=raw.get("department", ""),
        tags=raw.get("tags", []),
        filename=raw.get("filename") or None,
        document_type=raw.get("document_type") or None,
        chunk_index=raw.get("chunk_index") or None,
        chunk_count=raw.get("chunk_count") or None,
        effective_date=raw.get("effective_date") or None,
        author=raw.get("author") or None,
        version=raw.get("version", "1.0.0"),
    )


class RAGServiceError(Exception):
    pass


class RAGInitializationError(RAGServiceError):
    pass


class RAGIngestionError(RAGServiceError):
    pass


class RAGDeletionError(RAGServiceError):
    pass


class RAGRetrievalError(RAGServiceError):
    pass


class RAGService:
    def __init__(
        self,
        embedding_function: Embeddings,
        persist_directory: str = "./chroma_db",
        collection_name: str = "rh_documents",
    ) -> None:
        self._embedding_function = embedding_function
        self._persist_directory = persist_directory
        self._collection_name = collection_name
        self._vectorstore: Chroma | None = None

    # ------------------------------------------------------------------
    # Cycle de vie
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        try:
            self._vectorstore = Chroma(
                persist_directory=self._persist_directory,
                embedding_function=self._embedding_function,
                collection_name=self._collection_name,
                collection_metadata=_COLLECTION_METADATA,
            )
        except Exception as exc:
            raise RAGInitializationError(
                f"Impossible d'initialiser la collection '{self._collection_name}': {exc}"
            ) from exc
        logger.info("RAGService prêt — collection '%s' (cosine)", self._collection_name)

    @property
    def is_initialized(self) -> bool:
        return self._vectorstore is not None

    def _store(self) -> Chroma:
        if self._vectorstore is None:
            raise RAGInitializationError("RAGService n'est pas initialisé. Appelle initialize().")
        return self._vectorstore

    # ------------------------------------------------------------------
    # Identifiants et conversion
    # ------------------------------------------------------------------

    @staticmethod
    def _document_id(doc: DocumentIngestion) -> str:
        """ID stable : « fichier:position_du_chunk ».

        Indépendant du contenu et de l'ordre du batch, donc identique que l'on
        indexe un fichier seul ou tout le dossier. Sans nom de fichier, on
        retombe sur un hash du contenu.
        """
        meta = doc.metadata
        if meta.filename:
            return f"{meta.filename}:{meta.chunk_index or 0}"
        return hashlib.md5(doc.content.encode("utf-8")).hexdigest()

    def _to_lc_document(self, doc: DocumentIngestion) -> LCDocument:
        doc_id = self._document_id(doc)
        return LCDocument(
            page_content=doc.content,
            id=doc_id,
            metadata=_to_chroma(doc.metadata, doc_id),
        )

    def _upsert(self, documents: list[LCDocument]) -> None:
        """Supprime les IDs existants puis ajoute (évite les doublons au re-seed)."""
        store = self._store()
        ids = [d.id for d in documents]
        stale = store.get(ids=ids, include=[]).get("ids", [])
        if stale:
            store.delete(ids=stale)
        store.add_documents(documents, ids=ids)

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def ingest_batch(self, documents: list[DocumentIngestion]) -> list[str]:
        self._store()  # vérifie l'initialisation
        if not documents:
            return []
        try:
            # dict : dédoublonne les IDs identiques au sein du batch (le dernier gagne)
            by_id = {d.id: d for d in map(self._to_lc_document, documents)}
            lc_docs = list(by_id.values())
            self._upsert(lc_docs)
        except Exception as exc:
            raise RAGIngestionError(f"Échec de l'ingestion : {exc}") from exc
        logger.info("Ingestion OK — %d chunk(s)", len(lc_docs))
        return list(by_id)

    def ingest(self, document: DocumentIngestion) -> str:
        return self.ingest_batch([document])[0]

    # ------------------------------------------------------------------
    # Suppression
    # ------------------------------------------------------------------

    def delete_batch(self, documents: list[DocumentIngestion]) -> list[str]:
        store = self._store()
        ids = [self._document_id(d) for d in documents]
        if not ids:
            return []
        try:
            existing = store.get(ids=ids, include=[]).get("ids", [])
            if existing:
                store.delete(ids=existing)
        except Exception as exc:
            raise RAGDeletionError(f"Échec de la suppression : {exc}") from exc
        logger.info("Suppression OK — %d chunk(s)", len(existing))
        return existing

    def delete_by_filename(self, filename: str) -> list[str]:
        """Supprime tous les chunks d'un fichier (à appeler avant de le réindexer)."""
        store = self._store()
        if not filename:
            return []
        try:
            ids = store.get(where={"filename": {"$eq": filename}}, include=[]).get("ids", [])
            if ids:
                store.delete(ids=ids)
        except Exception as exc:
            raise RAGDeletionError(f"Échec de la suppression de '{filename}' : {exc}") from exc
        logger.info("Suppression de '%s' — %d chunk(s)", filename, len(ids))
        return ids

    # ------------------------------------------------------------------
    # Recherche vectorielle (le reranking est fait dans retriever.py)
    # ------------------------------------------------------------------

    @staticmethod
    def _build_filter(query: DocumentSearchQuery) -> dict | None:
        clauses: list[dict] = []
        if query.category is not None:
            clauses.append({"category": {"$eq": query.category.value}})
        if query.department:
            clauses.append({"department": {"$eq": query.department}})
        clauses.extend({"tags": {"$contains": tag}} for tag in (query.tags or []))

        if not clauses:
            return None
        return clauses[0] if len(clauses) == 1 else {"$and": clauses}

    def vector_search(self, query: DocumentSearchQuery) -> list[DocumentSearchResult]:
        """Filtres + similarité cosinus + seuil. Renvoie au moins CANDIDATE_POOL
        candidats, ni triés par le reranker ni coupés à top_k."""
        store = self._store()
        try:
            raw_results = store.similarity_search_with_score(
                query.query,
                k=max(query.top_k, CANDIDATE_POOL),
                filter=self._build_filter(query),
            )
        except Exception as exc:
            raise RAGRetrievalError(f"Échec de la recherche vectorielle : {exc}") from exc

        results: list[DocumentSearchResult] = []
        for doc, distance in raw_results:
            similarity = 1.0 - distance  # distance cosinus -> similarité dans [-1, 1]
            if similarity < query.similarity_threshold:
                continue
            results.append(
                DocumentSearchResult(
                    document_id=doc.metadata.get("document_id", ""),
                    content=doc.page_content,
                    metadata=_from_chroma(doc.metadata),
                    score=similarity,
                )
            )
        return results


def build_rag_service() -> RAGService:
    """Construit et initialise un RAGService à partir des settings."""
    from langchain_ollama import OllamaEmbeddings  # pip install langchain-ollama

    from core.config import get_settings

    settings = get_settings()
    rag = RAGService(
        embedding_function=OllamaEmbeddings(
            model=settings.ollama_embedding_model,
            base_url=settings.ollama_base_url,
        ),
        persist_directory=settings.chroma_persist_dir,
        collection_name=settings.chroma_collection_name,
    )
    rag.initialize()
    return rag