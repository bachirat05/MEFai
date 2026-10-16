from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.firebase_auth import (
    ManagerResolutionError,
    resolve_manager_email,
)
from Backend.sqlite.leave_models import LeaveRequestModel
from schemas.workflow import (
    DemandeConge,
    DemandeCongeResponse,
)
from services.audit.activity_log_service import (
    LEAVE_CREATED,
    safe_log_activity,
)
from services.workflows.n8n_service import (
    N8nService,
    N8nServiceError,
)


logger = logging.getLogger(__name__)


class LeaveSubmissionError(Exception):
    pass


class NoManagerAvailableError(LeaveSubmissionError):
    pass


async def submit_leave_request(
    *,
    demande: DemandeConge,
    user: dict[str, Any],
    db: Session,
    n8n_service: N8nService,
) -> DemandeCongeResponse:
    try:
        manager_email = resolve_manager_email()
    except ManagerResolutionError as exc:
        raise NoManagerAvailableError(
            "Aucun manager valide n'est configuré pour recevoir la demande."
        ) from exc

    result = await n8n_service.soumettre_demande_conge(
        demande,
        manager_email=manager_email,
    )

    statut = "pending"
    message = (
        "Demande transmise au manager et "
        "en attente de validation."
    )

    demande_id = result.get("demande_id")
    if not demande_id:
        logger.error(
            "n8n response missing demande_id: %s",
            result,
        )
        raise N8nServiceError(
            "n8n response does not contain a valid demande_id"
        )

    leave_request = LeaveRequestModel(
        demande_id=demande_id,
        user_uid=user.get("uid", ""),
        employee_email=user.get("email", ""),
        employe_id=demande.employe_id,
        type_conge=demande.type_conge.value,
        date_debut=demande.date_debut,
        date_fin=demande.date_fin,
        motif=demande.motif,
        statut=statut,
        message=message,
    )

    try:
        db.add(leave_request)
        db.commit()
        db.refresh(leave_request)

        logger.info(
            "Leave request saved - demande_id=%s, user_uid=%s",
            demande_id,
            user.get("uid", ""),
        )

        safe_log_activity(
            db,
            user=user,
            action=LEAVE_CREATED,
            resource="leave_request",
            details={
                "demande_id": demande_id,
                "type_conge": demande.type_conge.value,
            },
        )

    except Exception:
        db.rollback()
        raise

    return DemandeCongeResponse(
        statut=statut,
        message=message,
        demande_id=demande_id,
    )
