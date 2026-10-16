from __future__ import annotations

import hashlib
import logging

from langchain_chroma import Chroma
from langchain_core.documents import Document as LCDocument
from langchain_core.embeddings import Embeddings

from schemas.document import DocumentCategory, DocumentIngestion, DocumentMetadata, DocumentSearchQuery, DocumentSearchResult, DocumentSource

logger = logging.getLogger(__name__)

# ChromaDB HNSW index configuration: force Cosine distance so that
# similarity_search_with_score returns cosine distances in [0, 2].
_COLLECTION_METADATA = {"hnsw:space": "cosine"}


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
    def __init__(self, embedding_function: Embeddings, persist_directory: str = "./chroma_db", collection_name: str = "rh_documents") -> None:
        self._embedding_function = embedding_function
        self._persist_directory = persist_directory
        self._collection_name = collection_name
        self._vectorstore: Chroma | None = None
        self._initialized = False
        logger.info("RAGService instantiated for collection '%s' at '%s'", collection_name, persist_directory)

    def initialize(self) -> None:
        try:
            self._vectorstore = Chroma(
                persist_directory=self._persist_directory,
                embedding_function=self._embedding_function,
                collection_name=self._collection_name,
                collection_metadata=_COLLECTION_METADATA,
            )
            self._initialized = True
            logger.info("RAGService initialized — ChromaDB collection '%s' ready (space=cosine)", self._collection_name)
        except Exception as exc:
            logger.error("RAG initialization failed for collection '%s': %s", self._collection_name, exc)
            raise RAGInitializationError(f"Failed to initialize RAG collection '{self._collection_name}': {exc}") from exc

    @staticmethod
    def _compute_document_id(content: str) -> str:
        """Deterministic MD5 of the content — stable across re-seeds."""
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _build_lc_document(document: DocumentIngestion, doc_id: str) -> LCDocument:
        return LCDocument(
            page_content=document.content,
            id=doc_id,
            metadata={
                "document_id": doc_id,
                "category": document.metadata.category.value,
                "source": document.metadata.source.value,
                "department": document.metadata.department,
                "tags": document.metadata.tags,
                "filename": document.metadata.filename or "",
                "document_type": document.metadata.document_type or "",
                "chunk_index": document.metadata.chunk_index or 0,
                "chunk_count": document.metadata.chunk_count or 0,
                "effective_date": document.metadata.effective_date or "",
                "author": document.metadata.author or "",
                "version": document.metadata.version,
            },
        )

    def _upsert(self, documents: list[LCDocument], ids: list[str]) -> None:
        """Upsert semantics on top of ChromaDB's add (no native upsert in this version).

        Existing IDs are deleted first, then documents are added, so re-seeding
        with deterministic MD5 IDs updates in place instead of duplicating.
        """
        existing = self._vectorstore.get(ids=ids, include=[])
        stale_ids = existing.get("ids", [])
        if stale_ids:
            self._vectorstore.delete(ids=stale_ids)
        self._vectorstore.add_documents(documents, ids=ids)

    def ingest(self, document: DocumentIngestion) -> str:
        if not self._initialized or self._vectorstore is None:
            raise RAGInitializationError("RAGService is not initialized. Call initialize() first.")

        try:
            doc_id = self._compute_document_id(document.content)
            self._upsert(
                documents=[self._build_lc_document(document, doc_id)],
                ids=[doc_id],
            )
            logger.info("Document ingested (upsert) — id: '%s', category: '%s'", doc_id, document.metadata.category.value)
            return doc_id
        except Exception as exc:
            logger.error("Ingestion failed: %s", exc)
            raise RAGIngestionError(f"Failed to ingest document: {exc}") from exc

    def ingest_batch(self, documents: list[DocumentIngestion]) -> list[str]:
        if not self._initialized or self._vectorstore is None:
            raise RAGInitializationError("RAGService is not initialized. Call initialize() first.")

        try:
            lc_docs: list[LCDocument] = []
            doc_ids: list[str] = []
            for index, document in enumerate(documents):
                unique_key = f"{index}:{document.content}"
                doc_id = self._compute_document_id(
                    unique_key)
                doc_ids.append(doc_id)
                lc_docs.append(
                    self._build_lc_document(document, doc_id))
            self._upsert(documents=lc_docs, ids=doc_ids)
            logger.info("Batch ingestion successful (upsert) — %d documents", len(doc_ids))
            return doc_ids

        except Exception as exc:
            logger.error("Batch ingestion failed: %s", exc)
            raise RAGIngestionError(f"Failed to batch ingest documents: {exc}") from exc

    def delete_batch(self, documents: list[DocumentIngestion]) -> list[str]:
        if not self._initialized or self._vectorstore is None:
            raise RAGInitializationError("RAGService is not initialized. Call initialize() first.")

        try:
            doc_ids = [
                self._compute_document_id(document.content)
                for document in documents
            ]

            if not doc_ids:
                logger.info("Batch deletion skipped — no document ids provided")
                return []

            existing = self._vectorstore.get(ids=doc_ids, include=[])
            existing_ids = existing.get("ids", [])

            if existing_ids:
                self._vectorstore.delete(ids=existing_ids)

            logger.info("Batch deletion successful — %d documents", len(existing_ids))
            return existing_ids

        except Exception as exc:
            logger.error("Batch deletion failed: %s", exc)
            raise RAGDeletionError(f"Failed to batch delete documents: {exc}") from exc

    def delete_by_tag(self, tag: str) -> list[str]:
        if not self._initialized or self._vectorstore is None:
            raise RAGInitializationError("RAGService is not initialized. Call initialize() first.")

        try:
            if not tag:
                logger.info("Tag deletion skipped — empty tag")
                return []

            matching_ids: list[str] = []

            try:
                filtered = self._vectorstore.get(
                    where={
                        "tags": {
                            "$contains": tag,
                        },
                    },
                    include=[],
                )
                matching_ids = filtered.get("ids", [])
            except Exception:
                all_items = self._vectorstore.get(
                    include=["metadatas"],
                )
                ids = all_items.get("ids", [])
                metadatas = all_items.get("metadatas", [])

                matching_ids = [
                    doc_id
                    for doc_id, metadata in zip(ids, metadatas)
                    if tag in metadata.get("tags", [])
                ]

            if matching_ids:
                self._vectorstore.delete(
                    ids=matching_ids
                )

            logger.info(
                "Tag deletion successful — tag='%s', chunks=%d",
                tag,
                len(matching_ids),
            )
            return matching_ids

        except Exception as exc:
            logger.error(
                "Tag deletion failed for tag '%s': %s",
                tag,
                exc,
            )
            raise RAGDeletionError(f"Failed to delete documents by tag: {exc}") from exc

    def search(self, query: DocumentSearchQuery) -> list[DocumentSearchResult]:
        """Pure vector search (filters + similarity threshold).

        Returns up to max(top_k, 30) candidates, NOT re-ranked and NOT cut to
        top_k. Re-ranking is done by services.rag.retriever.
        """
        if not self._initialized or self._vectorstore is None:
            raise RAGInitializationError("RAGService is not initialized. Call initialize() first.")

        try:
            filters: list[dict] = []
            if query.category is not None:
                filters.append({"category": {"$eq": query.category.value}})
            if query.department:
                filters.append({"department": {"$eq": query.department}})
            if query.tags:
                for tag in query.tags:
                    filters.append({"tags": {"$contains": tag}})

            filter_dict: dict | None = None
            if len(filters) == 1:
                filter_dict = filters[0]
            elif len(filters) > 1:
                filter_dict = {"$and": filters}

            # Cosine space: ChromaDB returns cosine distance in [0, 2].
            # Convert to true cosine similarity in [-1, 1].
            candidate_k = max(
                query.top_k,
                30,
            )

            results = self._vectorstore.similarity_search_with_score(
                query.query,
                k=candidate_k,
                filter=filter_dict,
            )

            search_results: list[DocumentSearchResult] = []
            for doc, distance in results:
                similarity = 1.0 - distance
                if similarity < query.similarity_threshold:
                    continue
                meta = doc.metadata
                metadata = DocumentMetadata(
                    category=DocumentCategory(meta.get("category", DocumentCategory.OTHER.value)),
                    source=DocumentSource(meta.get("source", DocumentSource.MANUAL.value)),
                    department=meta.get("department", ""),
                    tags=meta.get("tags", []),
                    filename=meta.get("filename") or None,
                    document_type=meta.get("document_type") or None,
                    chunk_index=meta.get("chunk_index") or None,
                    chunk_count=meta.get("chunk_count") or None,
                    effective_date=meta.get("effective_date") or None,
                    author=meta.get("author") or None,
                    version=meta.get("version", "1.0.0"),
                )
                search_results.append(
                    DocumentSearchResult(
                        document_id=meta.get("document_id", ""),
                        content=doc.page_content,
                        metadata=metadata,
                        score=similarity,
                    )
                )

            logger.info(
                "Vector search completed — query='%s…', candidates=%d",
                query.query[:60],
                len(search_results),
            )
            return search_results
        except Exception as exc:
            logger.error("Search failed for query '%s…': %s", query.query[:60], exc)
            raise RAGRetrievalError(f"Search failed: {exc}") from exc

    @property
    def is_initialized(self) -> bool:
        return self._initialized


def build_rag_service() -> RAGService:
    """Build and initialize a RAGService from application settings."""
    from langchain_community.embeddings import OllamaEmbeddings

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