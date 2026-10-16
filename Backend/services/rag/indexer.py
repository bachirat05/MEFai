"""Index documents into ChromaDB (replaces seed_documents.py).

Run from the backend root:
    python -m services.rag.indexer
"""

from __future__ import annotations

from pathlib import Path

from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
)

from schemas.document import (
    DocumentCategory,
    DocumentIngestion,
    DocumentMetadata,
    DocumentSource,
)
from services.rag.loader import (
    list_files,
    read_document,
)
from services.rag.rag_service import (
    RAGService,
    build_rag_service,
)


DOCUMENTS_DIR = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "documents"
)


TEXT_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=200,
    length_function=len,
    separators=[
        "\n\n",
        "\n",
        ". ",
        " ",
        "",
    ],
    keep_separator=True,
)


# ============================================================
# METADATA
# ============================================================


def detect_category(
    file_path: Path,
) -> DocumentCategory:
    filename = (
        file_path.stem.lower()
    )

    if any(
        keyword in filename
        for keyword in (
            "securite",
            "sécurité",
            "confidentialite",
            "confidentialité",
            "reglement",
            "règlement",
            "conformite",
            "conformité",
        )
    ):
        return (
            DocumentCategory.COMPLIANCE
        )

    if any(
        keyword in filename
        for keyword in (
            "procedure",
            "procédure",
        )
    ):
        return (
            DocumentCategory.HR_PROCEDURE
        )

    if any(
        keyword in filename
        for keyword in (
            "conge",
            "congé",
            "leave",
        )
    ):
        return (
            DocumentCategory.LEAVE_POLICY
        )

    if any(
        keyword in filename
        for keyword in (
            "formation",
            "training",
            "certification",
            "certificat",
            "certif",
        )
    ):
        return (
            DocumentCategory.TRAINING
        )

    if any(
        keyword in filename
        for keyword in (
            "onboarding",
            "integration",
            "intégration",
        )
    ):
        return (
            DocumentCategory.ONBOARDING
        )

    if any(
        keyword in filename
        for keyword in (
            "avantage",
            "avantages",
            "benefit",
            "benefits",
            "prime",
            "indemnite",
            "indemnité",
            "transport",
        )
    ):
        return (
            DocumentCategory.BENEFITS
        )

    if any(
        keyword in filename
        for keyword in (
            "politique",
            "teletravail",
            "télétravail",
        )
    ):
        return (
            DocumentCategory.RH_POLICY
        )

    return (
        DocumentCategory.OTHER
    )


def build_metadata(
    file_path: Path,
) -> DocumentMetadata:
    extension = file_path.suffix.lower()

    return DocumentMetadata(
        category=detect_category(
            file_path
        ),
        source=(
            DocumentSource.INTERNAL_WIKI
        ),
        department="RH",
        tags=[
            file_path.name,
            file_path.stem,
            extension,
            "document_interne",
        ],
        filename=file_path.name,
        document_type=extension.lstrip("."),
    )


# ============================================================
# CHUNKING
# ============================================================


def build_file_ingestions(
    file_path: Path,
) -> list[DocumentIngestion]:
    content = (
        read_document(file_path)
        .strip()
    )

    if not content:
        raise ValueError(
            "Le document est vide."
        )

    metadata = build_metadata(
        file_path
    )

    chunks = (
        TEXT_SPLITTER
        .split_text(content)
    )

    total_chunks = len(chunks)

    ingestions: list[
        DocumentIngestion
    ] = []

    for index, chunk in enumerate(
        chunks,
        start=1,
    ):
        cleaned_chunk = (
            chunk.strip()
        )

        if not cleaned_chunk:
            continue

        chunk_metadata = (
            DocumentMetadata(
                category=metadata.category,
                source=metadata.source,
                department=metadata.department,
                tags=[
                    *metadata.tags,
                    (
                        f"chunk_"
                        f"{index}/"
                        f"{total_chunks}"
                    ),
                ],
                filename=metadata.filename,
                document_type=metadata.document_type,
                chunk_index=index,
                chunk_count=total_chunks,
            )
        )

        ingestions.append(
            DocumentIngestion(
                content=cleaned_chunk,
                metadata=chunk_metadata,
            )
        )

    return ingestions


# ============================================================
# INDEXING (ex seed_documents.py)
# ============================================================


def index_file(
    rag: RAGService,
    file_path: Path,
) -> list[str]:
    """Index a single file (usable from an upload endpoint)."""

    ingestions = build_file_ingestions(
        file_path
    )

    return rag.ingest_batch(
        ingestions
    )


def index_directory(
    rag: RAGService,
    directory: Path = DOCUMENTS_DIR,
) -> list[str]:
    """Load every supported file, chunk it and ingest all chunks in one batch."""

    if not directory.exists():
        print(
            "[WARNING] Documents directory "
            f"not found: {directory}"
        )

        return []

    files = list_files(directory)

    print(
        f"[FILES] {len(files)} "
        "supported file(s) found."
    )

    ingestions: list[
        DocumentIngestion
    ] = []

    for file_path in files:
        print(
            f"[READ] {file_path.name}"
        )

        try:
            file_ingestions = (
                build_file_ingestions(
                    file_path
                )
            )

        except Exception as exc:
            print(
                "[ERROR] Cannot index "
                f"{file_path.name}: {exc}"
            )

            continue

        print(
            "[CHUNKING] "
            f"{file_path.name} "
            f"-> {len(file_ingestions)} chunk(s)"
        )

        ingestions.extend(
            file_ingestions
        )

    if not ingestions:
        print(
            "[WARNING] No chunks "
            "generated."
        )

        return []

    print(
        "\n"
        f"[SUMMARY] "
        f"{len(files)} document(s) "
        f"-> {len(ingestions)} chunk(s)"
    )

    return rag.ingest_batch(
        ingestions
    )


# ============================================================
# MAIN
# ============================================================


def main() -> None:
    from core.logging import setup_logging

    setup_logging()

    print(
        "\n"
        "========================================"
    )

    print(
        " CORTEX AI - DOCUMENT INGESTION"
    )

    print(
        "========================================"
    )

    print(
        f"[DIR] {DOCUMENTS_DIR}"
    )

    rag = build_rag_service()

    ids = index_directory(
        rag
    )

    if not ids:
        print(
            "[WARNING] No documents "
            "to ingest."
        )

        return

    print(
        "\n"
        f"[OK] {len(ids)} chunks "
        "ingérés dans ChromaDB."
    )

    print(
        "\nIDs:"
    )

    for chunk_id in ids:
        print(
            f" - {chunk_id}"
        )


if __name__ == "__main__":
    main()