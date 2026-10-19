from __future__ import annotations

import logging
import shutil

from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
)
from sqlalchemy.orm import Session

from app.firebase_auth import require_admin , require_admin_or_n8n
from Backend.sqlite.database import get_db
from services.audit.activity_log_service import (
    DOCUMENT_DELETE,
    DOCUMENT_UPLOAD,
    safe_log_activity,
)

from services.rag.indexer import (
    build_file_ingestions,
)


router = APIRouter(
    prefix="/api/documents",
    tags=["documents"],
)

logger = logging.getLogger(
    __name__
)

ROOT_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
    .parent
)

DOCUMENTS_DIR = (
    ROOT_DIR
    / "data"
    / "documents"
)

SUPPORTED_EXTENSIONS = {
    ".txt",
    ".pdf",
    ".docx",
}


def resolve_document_path(
    filename: str,
) -> Path:
    safe_name = Path(filename).name

    if (
        not safe_name
        or safe_name != filename
    ):
        raise HTTPException(
            status_code=400,
            detail="Nom de fichier invalide.",
        )

    extension = (
        Path(safe_name)
        .suffix
        .lower()
    )

    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Format non supporte. "
                "Formats autorises : TXT, PDF, DOCX."
            ),
        )

    documents_root = DOCUMENTS_DIR.resolve()
    file_path = (
        DOCUMENTS_DIR
        / safe_name
    ).resolve()

    if (
        file_path.parent
        != documents_root
    ):
        raise HTTPException(
            status_code=400,
            detail="Nom de fichier invalide.",
        )

    return file_path


@router.get("")
async def list_documents(
    user=Depends(require_admin),
):
    if not DOCUMENTS_DIR.exists():
        return []

    documents = []

    for file_path in sorted(
        DOCUMENTS_DIR.iterdir()
    ):
        if (
            not file_path.is_file()
            or file_path.suffix.lower()
            not in SUPPORTED_EXTENSIONS
        ):
            continue

        stat = file_path.stat()

        documents.append(
            {
                "name": file_path.name,
                "type": (
                    file_path
                    .suffix
                    .lower()
                    .lstrip(".")
                ),
                "size": stat.st_size,
            }
        )

    return documents


@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    user=Depends(require_admin_or_n8n),
    db: Session = Depends(get_db),
):
    destination: Path | None = None

    try:
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="Nom de fichier invalide.",
            )

        safe_name = Path(
            file.filename
        ).name

        extension = (
            Path(safe_name)
            .suffix
            .lower()
        )

        if extension not in SUPPORTED_EXTENSIONS:
            logger.warning(
                "Rejected unsupported document upload: %s",
                safe_name,
            )

            raise HTTPException(
                status_code=400,
                detail=(
                    "Format non supporte. "
                    "Formats autorises : TXT, PDF, DOCX."
                ),
            )

        DOCUMENTS_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        destination = (
            DOCUMENTS_DIR
            / safe_name
        )

        if destination.exists():
            logger.warning(
                "Rejected duplicate document upload: %s",
                safe_name,
            )

            raise HTTPException(
                status_code=409,
                detail=(
                    "Un document portant ce nom existe deja."
                ),
            )

        try:
            with destination.open("wb") as buffer:
                shutil.copyfileobj(
                    file.file,
                    buffer,
                )

        except Exception as exc:
            destination.unlink(
                missing_ok=True
            )

            logger.error(
                "Document write failed for %s: %s",
                safe_name,
                exc,
            )

            raise HTTPException(
                status_code=500,
                detail=(
                    "Impossible d'enregistrer "
                    "le document."
                ),
            ) from exc

        file_size = destination.stat().st_size

        logger.info(
            "Document uploaded to disk: %s (%d bytes)",
            safe_name,
            file_size,
        )

        try:
            ingestions = build_file_ingestions(
                destination
            )

            if not ingestions:
                raise ValueError(
                    "Aucun chunk n'a ete genere."
                )

        except Exception as exc:
            destination.unlink(
                missing_ok=True
            )

            logger.warning(
                "Document parsing failed for %s: %s",
                safe_name,
                exc,
            )

            raise HTTPException(
                status_code=400,
                detail=(
                    "Impossible de traiter "
                    f"le document : {exc}"
                ),
            ) from exc

        rag_service = getattr(
            request.app.state,
            "rag_service",
            None,
        )

        if (
            rag_service is None
            or not rag_service.is_initialized
        ):
            destination.unlink(
                missing_ok=True
            )

            logger.error(
                "Document upload refused because RAG is unavailable: %s",
                safe_name,
            )

            raise HTTPException(
                status_code=503,
                detail=(
                    "Service RAG indisponible. "
                    "Le document n'a pas ete ajoute."
                ),
            )

        try:
            rag_service.ingest_batch(
                ingestions
            )

        except Exception as exc:
            destination.unlink(
                missing_ok=True
            )

            logger.error(
                "RAG ingestion failed for %s: %s",
                safe_name,
                exc,
            )

            raise HTTPException(
                status_code=500,
                detail=(
                    "Impossible d'indexer "
                    "le document dans le RAG."
                ),
            ) from exc

        logger.info(
            "Document indexed successfully: %s (%d chunks)",
            safe_name,
            len(ingestions),
        )

        safe_log_activity(
            db,
            user=user,
            action=DOCUMENT_UPLOAD,
            resource="documents",
            details={
                "filename": safe_name,
                "type": extension.lstrip("."),
                "chunks": len(ingestions),
            },
        )

        return {
            "message": (
                "Document ajoute et indexe avec succes."
            ),
            "name": safe_name,
            "type": extension.lstrip("."),
            "size": file_size,
            "chunks": len(ingestions),
            "rag_ingested": True,
        }

    finally:
        await file.close()


@router.delete("/{filename}")
async def delete_document(
    filename: str,
    request: Request,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    file_path = resolve_document_path(
        filename
    )

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Document introuvable.",
        )

    if not file_path.is_file():
        raise HTTPException(
            status_code=400,
            detail="Le document cible est invalide.",
        )

    try:
        ingestions = build_file_ingestions(
            file_path
        )

        if not ingestions:
            raise ValueError(
                "Aucun chunk n'a ete genere."
            )

    except Exception as exc:
        logger.warning(
            "Document deletion refused because parsing failed for %s: %s",
            file_path.name,
            exc,
        )

        raise HTTPException(
            status_code=400,
            detail=(
                "Impossible de traiter "
                f"le document avant suppression : {exc}"
            ),
        ) from exc

    rag_service = getattr(
        request.app.state,
        "rag_service",
        None,
    )

    if (
        rag_service is None
        or not rag_service.is_initialized
    ):
        logger.error(
            "Document deletion refused because RAG is unavailable: %s",
            file_path.name,
        )

        raise HTTPException(
            status_code=503,
            detail=(
                "Service RAG indisponible. "
                "Le document n'a pas ete supprime."
            ),
        )

    try:
        deleted_ids = rag_service.delete_batch(
            ingestions
        )

    except Exception as exc:
        logger.error(
            "RAG deletion failed for %s: %s",
            file_path.name,
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Impossible de supprimer "
                "les chunks du document dans le RAG."
            ),
        ) from exc

    try:
        file_path.unlink()

    except Exception as exc:
        logger.error(
            "Disk deletion failed after RAG deletion for %s: %s",
            file_path.name,
            exc,
        )

        try:
            rag_service.ingest_batch(
                ingestions
            )

            logger.info(
                "RAG rollback succeeded after disk deletion failure for %s",
                file_path.name,
            )

        except Exception as rollback_exc:
            logger.error(
                "RAG rollback failed after disk deletion failure for %s: %s",
                file_path.name,
                rollback_exc,
            )

        raise HTTPException(
            status_code=500,
            detail=(
                "Impossible de supprimer le fichier. "
                "Rollback RAG tente."
            ),
        ) from exc

    logger.info(
        "Document deleted successfully: %s (%d chunks)",
        file_path.name,
        len(deleted_ids),
    )

    safe_log_activity(
        db,
        user=user,
        action=DOCUMENT_DELETE,
        resource="documents",
        details={
            "filename": file_path.name,
            "chunks_deleted": len(deleted_ids),
        },
    )

    return {
        "message": "Document supprime avec succes.",
        "name": file_path.name,
        "chunks_deleted": len(deleted_ids),
    }

