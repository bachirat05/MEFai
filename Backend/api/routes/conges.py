from __future__ import annotations

import logging

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlalchemy.orm import Session

from app.firebase_auth import (
    require_manager,
    verify_firebase_token,
)
from core.config import (
    get_settings,
)
from Backend.sqlite.database import (
    get_db,
)
from Backend.sqlite.leave_models import (
    LeaveRequestModel,
)
from schemas.workflow import (
    DemandeConge,
    DemandeCongeResponse,
    LeaveRequestStatusUpdate,
)
from services.workflows.n8n_service import (
    N8nService,
    N8nServiceError,
)
from services.workflows.leave_submission_service import (
    NoManagerAvailableError,
    submit_leave_request,
)
from services.audit.activity_log_service import (
    LEAVE_ACCEPTED,
    LEAVE_REJECTED,
    safe_log_activity,
)


logger = logging.getLogger(__name__)

settings = get_settings()


router = APIRouter(
    prefix="/api",
    tags=["conges"],
)


n8n_service = N8nService(
    webhook_url=settings.n8n_webhook_url,
    secret_token=settings.n8n_secret_token,
    timeout_seconds=settings.n8n_timeout_seconds,
    status_notification_webhook_url=settings.n8n_status_notification_webhook_url,
)


@router.post(
    "/conges",
    response_model=DemandeCongeResponse,
)
async def soumettre_conge(
    demande: DemandeConge,
    user=Depends(
        verify_firebase_token
    ),
    db: Session = Depends(
        get_db
    ),
) -> DemandeCongeResponse:
    try:
        return await submit_leave_request(
            demande=demande,
            user=user,
            db=db,
            n8n_service=n8n_service,
        )

    except NoManagerAvailableError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except N8nServiceError as exc:
        logger.error(
            "n8n workflow error: %s",
            exc,
        )

        raise HTTPException(
            status_code=503,
            detail=(
                "Le service de workflow "
                "n8n est indisponible."
            ),
        ) from exc

    except Exception as exc:
        db.rollback()

        logger.exception(
            "Unexpected error submitting "
            "leave request"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Erreur lors de la "
                "soumission de la "
                "demande de congé."
            ),
        ) from exc

@router.get("/conges")
async def get_mes_conges(
    user=Depends(
        verify_firebase_token
    ),
    db: Session = Depends(
        get_db
    ),
):
    user_uid = user.get(
        "uid",
        "",
    )

    demandes = (
        db.query(
            LeaveRequestModel
        )
        .filter(
            LeaveRequestModel.user_uid
            == user_uid
        )
        .order_by(
            LeaveRequestModel.created_at.desc()
        )
        .all()
    )

    return [
        {
            "demande_id":
                demande.demande_id,

            "employe_id":
                demande.employe_id,

            "type_conge":
                demande.type_conge,

            "date_debut":
                demande.date_debut,

            "date_fin":
                demande.date_fin,

            "motif":
                demande.motif,

            "statut":
                demande.statut,

            "message":
                demande.message,

            "created_at":
                demande.created_at,
        }
        for demande in demandes
    ]


def _leave_request_response(demande: LeaveRequestModel) -> dict:
    return {
        "demande_id": demande.demande_id,
        "user_uid": demande.user_uid,
        "employe_id": demande.employe_id,
        "employee_email": demande.employee_email,
        "type_conge": demande.type_conge,
        "date_debut": demande.date_debut,
        "date_fin": demande.date_fin,
        "motif": demande.motif,
        "statut": demande.statut,
        "message": demande.message,
        "created_at": demande.created_at,
    }


@router.get("/manager/conges")
async def get_manager_conges(
    user=Depends(require_manager),
    db: Session = Depends(get_db),
):
    demandes = (
        db.query(LeaveRequestModel)
        .order_by(LeaveRequestModel.created_at.desc())
        .all()
    )

    return [_leave_request_response(demande) for demande in demandes]


@router.patch("/manager/conges/{demande_id}")
async def update_manager_conge(
    demande_id: str,
    update: LeaveRequestStatusUpdate,
    user=Depends(require_manager),
    db: Session = Depends(get_db),
):
    demande = (
        db.query(LeaveRequestModel)
        .filter(LeaveRequestModel.demande_id == demande_id)
        .first()
    )

    if demande is None:
        raise HTTPException(
            status_code=404,
            detail="Demande de congé introuvable",
        )

    # 1. Update database
    try:
        demande.statut = update.statut

        db.commit()
        db.refresh(demande)

        logger.info(
            "Leave request updated — demande_id=%s, statut=%s",
            demande.demande_id,
            demande.statut,
        )

        action = (
            LEAVE_ACCEPTED
            if demande.statut == "accepted"
            else LEAVE_REJECTED
        )

        safe_log_activity(
            db,
            user=user,
            action=action,
            resource="leave_request",
            details={
                "demande_id": demande.demande_id,
            },
        )

    except Exception as exc:
        db.rollback()

        logger.exception(
            "Unable to update leave request %s",
            demande_id,
        )

        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la mise à jour de la demande de congé.",
        ) from exc

    # 2. Send notification
    try:
        await n8n_service.notifier_statut_demande(
            email=demande.employee_email,
            demande_id=demande.demande_id,
            statut=demande.statut,
        )

        logger.info(
            "Employee notified — demande_id=%s, statut=%s",
            demande.demande_id,
            demande.statut,
        )

    except N8nServiceError as exc:
        logger.error(
            "Leave request updated but employee notification failed — "
            "demande_id=%s, error=%s",
            demande.demande_id,
            exc,
        )

    return _leave_request_response(demande)
