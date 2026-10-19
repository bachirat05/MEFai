from __future__ import annotations

import logging
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

from schemas.document import (
    DocumentCategory,
    DocumentIngestion,
    DocumentMetadata,
    DocumentSource,
)
from services.rag.loader import list_files, normalize_text, read_document
from services.rag.rag_service import RAGService, build_rag_service

logger = logging.getLogger(__name__)

DOCUMENTS_DIR = Path(__file__).resolve().parents[2] / "data" / "documents"

TEXT_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=200,
    length_function=len,
    separators=["\n\n", "\n", ". ", " ", ""],
    keep_separator=True,
)

# L'ordre compte : le premier groupe qui correspond gagne.
# Mots-clés sans accent : le nom du fichier est normalisé avant comparaison.
_CATEGORY_RULES: list[tuple[DocumentCategory, tuple[str, ...]]] = [
    (DocumentCategory.COMPLIANCE, ("securite", "confidentialite", "reglement", "conformite")),
    (DocumentCategory.HR_PROCEDURE, ("procedure",)),
    (DocumentCategory.LEAVE_POLICY, ("conge", "leave")),
    (DocumentCategory.TRAINING, ("formation", "training", "certif")),
    (DocumentCategory.ONBOARDING, ("onboarding", "integration")),
    (DocumentCategory.BENEFITS, ("avantage", "benefit", "prime", "indemnite", "transport")),
    (DocumentCategory.RH_POLICY, ("politique", "teletravail")),
]


# ------------------------------------------------------------------
# Métadonnées
# ------------------------------------------------------------------


def detect_category(file_path: Path) -> DocumentCategory:
    name = normalize_text(file_path.stem)
    for category, keywords in _CATEGORY_RULES:
        if any(keyword in name for keyword in keywords):
            return category
    return DocumentCategory.OTHER


def build_metadata(file_path: Path) -> DocumentMetadata:
    """Métadonnées communes à tous les chunks d'un fichier."""
    return DocumentMetadata(
        category=detect_category(file_path),
        source=DocumentSource.INTERNAL_WIKI,
        department="RH",
        tags=["document_interne"],
        filename=file_path.name,
        document_type=file_path.suffix.lower().lstrip("."),
    )


# ------------------------------------------------------------------
# Chunking
# ------------------------------------------------------------------


def build_file_ingestions(file_path: Path) -> list[DocumentIngestion]:
    content = read_document(file_path).strip()
    if not content:
        raise ValueError(f"Le document est vide : {file_path.name}")

    base_metadata = build_metadata(file_path)
    chunks = [c.strip() for c in TEXT_SPLITTER.split_text(content)]
    chunks = [c for c in chunks if c]
    total = len(chunks)

    return [
        DocumentIngestion(
            content=chunk,
            metadata=base_metadata.model_copy(
                update={"chunk_index": index, "chunk_count": total}
            ),
        )
        for index, chunk in enumerate(chunks, start=1)
    ]


# ------------------------------------------------------------------
# Indexation
# ------------------------------------------------------------------


def index_file(rag: RAGService, file_path: Path) -> list[str]:
    """Indexe (ou réindexe) un fichier. Utilisable depuis un endpoint d'upload.

    Les anciens chunks du fichier sont supprimés d'abord : si le fichier
    raccourcit, aucun chunk orphelin ne reste.
    """
    ingestions = build_file_ingestions(file_path)
    rag.delete_by_filename(file_path.name)
    return rag.ingest_batch(ingestions)


def index_directory(rag: RAGService, directory: Path = DOCUMENTS_DIR) -> list[str]:
    """Indexe tous les fichiers supportés ; un fichier en erreur n'arrête pas les autres."""
    if not directory.exists():
        logger.warning("Dossier de documents introuvable : %s", directory)
        return []

    files = list_files(directory)
    logger.info("%d fichier(s) supporté(s) trouvé(s) dans %s", len(files), directory)

    all_ids: list[str] = []
    for file_path in files:
        try:
            ids = index_file(rag, file_path)
        except Exception:
            logger.exception("Indexation impossible : %s", file_path.name)
            continue
        logger.info("%s -> %d chunk(s)", file_path.name, len(ids))
        all_ids.extend(ids)

    return all_ids


def main() -> None:
    from core.logging import setup_logging

    setup_logging()
    ids = index_directory(build_rag_service())

    if ids:
        logger.info("%d chunk(s) ingéré(s) dans ChromaDB.", len(ids))
    else:
        logger.warning("Aucun document ingéré.")


if __name__ == "__main__":
    main()