from __future__ import annotations

import logging
import uuid

import httpx

from schemas.workflow import DemandeConge

logger = logging.getLogger(__name__)


class N8nServiceError(Exception):
    pass


class N8nTimeoutError(N8nServiceError):
    pass


class N8nHTTPError(N8nServiceError):
    def __init__(
        self,
        message: str,
        status_code: int,
        response_body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class N8nService:
    def __init__(
        self,
        webhook_url: str,
        secret_token: str,
        timeout_seconds: float = 15.0,
        status_notification_webhook_url: str = "",
    ) -> None:
        self._webhook_url = webhook_url
        self._status_notification_webhook_url = (
            status_notification_webhook_url
        )
        self._secret_token = secret_token
        self._timeout = httpx.Timeout(
            timeout=timeout_seconds
        )

        logger.info(
            "N8nService initialized for webhook: %s",
            webhook_url,
        )

    async def soumettre_demande_conge(
        self,
        demande: DemandeConge,
        manager_email: str,
    ) -> dict:
        if not self._webhook_url:
            raise N8nServiceError(
                "n8n_webhook_url is not configured"
            )

        payload = demande.model_dump(
            mode="json"
        )

        payload["manager_email"] = (
            manager_email
        )

        headers = {
            "Content-Type":
                "application/json",

            "Authorization":
                f"Bearer {self._secret_token}",
        }

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout
            ) as client:
                response = await client.post(
                    self._webhook_url,
                    json=payload,
                    headers=headers,
                )

                response.raise_for_status()

                logger.info(
                    "n8n status: %s",
                    response.status_code,
                )

                logger.info(
                    "n8n content-type: %s",
                    response.headers.get(
                        "content-type"
                    ),
                )

                logger.info(
                    "n8n response: %s",
                    response.text,
                )

                # ========================================
                # VALIDATE RESPONSE BODY
                # ========================================

                # Si n8n retourne un corps vide (ex: erreur dans le workflow),
                # on génère un demande_id de secours plutôt que de planter.
                if not response.text.strip():
                    logger.warning(
                        "n8n webhook returned an empty body — "
                        "using fallback demande_id"
                    )
                    return {
                        "demande_id": f"CONGE-{uuid.uuid4().hex[:8].upper()}",
                        "statut": "en_attente",
                        "message": "Demande transmise. En attente de validation manager.",
                    }

                try:
                    data = response.json()

                except ValueError:
                    logger.warning(
                        "n8n webhook returned invalid JSON — "
                        "using fallback demande_id"
                    )
                    return {
                        "demande_id": f"CONGE-{uuid.uuid4().hex[:8].upper()}",
                        "statut": "en_attente",
                        "message": "Demande transmise. En attente de validation manager.",
                    }

                if not isinstance(data, dict):
                    logger.warning(
                        "n8n webhook returned unexpected format — "
                        "using fallback demande_id"
                    )
                    return {
                        "demande_id": f"CONGE-{uuid.uuid4().hex[:8].upper()}",
                        "statut": "en_attente",
                        "message": "Demande transmise. En attente de validation manager.",
                    }

                # Si demande_id manquant, on en génère un
                if not data.get("demande_id"):
                    data["demande_id"] = f"CONGE-{uuid.uuid4().hex[:8].upper()}"
                    logger.warning(
                        "n8n response missing demande_id — generated: %s",
                        data["demande_id"],
                    )

                logger.info(
                    "Demande congé soumise avec succès — "
                    "employe_id=%s, statut=%s",
                    demande.employe_id,
                    data.get("statut", "unknown"),
                )

                return data

        except httpx.TimeoutException as exc:
            logger.error(
                "n8n webhook timeout: %s",
                exc,
            )

            raise N8nTimeoutError(
                "n8n webhook request "
                "timed out"
            ) from exc

        except httpx.HTTPStatusError as exc:
            logger.error(
                "n8n webhook returned "
                "HTTP %s: %s",
                exc.response.status_code,
                exc.response.text,
            )

            raise N8nHTTPError(
                (
                    "n8n webhook returned HTTP "
                    f"{exc.response.status_code}"
                ),
                exc.response.status_code,
                exc.response.text,
            ) from exc

        except httpx.ConnectError as exc:
            logger.error(
                "n8n webhook connection "
                "error: %s",
                exc,
            )

            raise N8nServiceError(
                "Cannot connect to "
                f"n8n webhook: {exc}"
            ) from exc

        except httpx.RequestError as exc:
            logger.error(
                "n8n webhook request "
                "error: %s",
                exc,
            )

            raise N8nServiceError(
                "n8n webhook request "
                f"failed: {exc}"
            ) from exc

    async def notifier_statut_demande(
        self,
        email: str,
        demande_id: str,
        statut: str,
    ) -> dict:
        if not (
            self
            ._status_notification_webhook_url
        ):
            raise N8nServiceError(
                "n8n_status_notification_"
                "webhook_url is not configured"
            )

        payload = {
            "email":
                email,

            "demande_id":
                demande_id,

            "statut":
                statut,
        }

        headers = {
            "Content-Type":
                "application/json",

            "Authorization":
                f"Bearer {self._secret_token}",
        }

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout
            ) as client:
                response = await client.post(
                    self
                    ._status_notification_webhook_url,
                    json=payload,
                    headers=headers,
                )

                response.raise_for_status()

                logger.info(
                    "Notification statut "
                    "envoyée — "
                    "demande_id=%s, "
                    "statut=%s, "
                    "email=%s",
                    demande_id,
                    statut,
                    email,
                )

                logger.info(
                    "n8n notification "
                    "status: %s",
                    response.status_code,
                )

                logger.info(
                    "n8n notification "
                    "content-type: %s",
                    response.headers.get(
                        "content-type"
                    ),
                )

                # ========================================
                # VALIDATE RESPONSE BODY
                # ========================================

                if not response.text.strip():
                    logger.error(
                        "n8n status notification "
                        "returned an empty "
                        "response body"
                    )

                    raise N8nServiceError(
                        "n8n status notification "
                        "returned an empty "
                        "response body"
                    )

                try:
                    data = response.json()

                except ValueError as exc:
                    logger.error(
                        "n8n status notification "
                        "returned invalid JSON"
                    )

                    raise N8nServiceError(
                        "n8n status notification "
                        "returned invalid JSON"
                    ) from exc

                if not isinstance(
                    data,
                    dict,
                ):
                    logger.error(
                        "n8n status notification "
                        "returned an unexpected "
                        "response format"
                    )

                    raise N8nServiceError(
                        "n8n status notification "
                        "returned an unexpected "
                        "response format"
                    )

                return data

        except httpx.TimeoutException as exc:
            logger.error(
                "n8n status notification "
                "timeout: %s",
                exc,
            )

            raise N8nTimeoutError(
                "n8n status notification "
                "webhook timed out"
            ) from exc

        except httpx.HTTPStatusError as exc:
            logger.error(
                "n8n status notification "
                "returned HTTP %s: %s",
                exc.response.status_code,
                exc.response.text,
            )

            raise N8nHTTPError(
                (
                    "n8n status notification "
                    "webhook returned HTTP "
                    f"{exc.response.status_code}"
                ),
                exc.response.status_code,
                exc.response.text,
            ) from exc

        except httpx.ConnectError as exc:
            logger.error(
                "n8n status notification "
                "connection error: %s",
                exc,
            )

            raise N8nServiceError(
                "Cannot connect to n8n "
                "status notification "
                f"webhook: {exc}"
            ) from exc

        except httpx.RequestError as exc:
            logger.error(
                "n8n status notification "
                "request error: %s",
                exc,
            )

            raise N8nServiceError(
                "n8n status notification "
                "webhook request "
                f"failed: {exc}"
            ) from exc