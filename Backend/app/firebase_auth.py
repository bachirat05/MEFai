from __future__ import annotations
import os
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, auth


from dotenv import load_dotenv
from fastapi import Depends, Header, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# =========================================================
# ENVIRONMENT
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)




# =========================================================
# FIREBASE ADMIN INITIALIZATION
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
FIREBASE_KEY = BASE_DIR / "firebase_admin_key.json"

if not firebase_admin._apps:
    cred = credentials.Certificate(str(FIREBASE_KEY))
    firebase_admin.initialize_app(cred)


# =========================================================
# VERIFY FIREBASE TOKEN
# =========================================================

firebase_bearer = HTTPBearer(
    auto_error=False,
    scheme_name="FirebaseBearer",
    description=(
        "Token Firebase ID au format Bearer. "
        "Utilisez le bouton Authorize de Swagger."
    ),
)


def _extract_token(
    credentials: HTTPAuthorizationCredentials | str | None,
) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Token Firebase manquant",
        )

    if isinstance(credentials, str):
        authorization = credentials

        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Format du token invalide",
            )

        token = authorization[len("Bearer "):].strip()
    else:
        if credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=401,
                detail="Format du token invalide",
            )

        token = credentials.credentials.strip()

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Token Firebase vide",
        )

    return token


async def verify_firebase_token(
    credentials: HTTPAuthorizationCredentials | str | None = Security(
        firebase_bearer
    ),
):
    token = _extract_token(credentials)

    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token

    except Exception as exc:
        raise HTTPException(
            status_code=401,
            detail="Token Firebase invalide ou expiré",
        ) from exc

async def verify_n8n_secret( x_n8n_secret: str | None = Header(default=None),):
    expected_secret = os.getenv("N8N_INTERNAL_SECRET")

    if not expected_secret:
        raise HTTPException(
            status_code=500,
            detail="N8N_INTERNAL_SECRET non configuré",
        )

    if x_n8n_secret != expected_secret:
        raise HTTPException(
            status_code=401,
            detail="Secret n8n invalide",
        )

    return True

# =========================================================
# REQUIRE ADMIN
# =========================================================

async def require_admin(
    user: dict = Depends(verify_firebase_token),
):
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Accès administrateur requis",
        )

    return user


async def require_manager_or_admin(
    user: dict = Depends(verify_firebase_token),
):
    if user.get("role") not in {"manager", "admin"}:
        raise HTTPException(
            status_code=403,
            detail="Accès manager ou administrateur requis",
        )

    return user



async def require_admin_or_n8n(
    authorization: str | None = Header(default=None),
    x_n8n_secret: str | None = Header(default=None),
):
    expected_secret = os.getenv("N8N_INTERNAL_SECRET")

    # =====================================================
    # N8N
    # =====================================================

    if x_n8n_secret is not None:

        if not expected_secret:
            raise HTTPException(
                status_code=500,
                detail="N8N_INTERNAL_SECRET non configuré",
            )

        if x_n8n_secret != expected_secret:
            raise HTTPException(
                status_code=401,
                detail="Secret n8n invalide",
            )

        print("✅ Authentification N8N réussie")

        return {
            "uid": "n8n-service",
            "email": "n8n@internal",
            "role": "admin",
            "auth_type": "n8n",
        }

    # =====================================================
    # FIREBASE
    # =====================================================

    user = await verify_firebase_token(authorization)

    if user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Accès administrateur requis",
        )

    return user


async def require_manager(
    user: dict = Depends(verify_firebase_token),
):
    if user.get("role") != "manager":
        raise HTTPException(
            status_code=403,
            detail="Accès manager requis",
        )

    return user


class ManagerResolutionError(Exception):
    pass


def resolve_manager_email() -> str:
    """
    Resolve the current manager from Firebase users.

    Temporary deterministic strategy while team hierarchy is not modeled:
    pick the first valid manager sorted by lowercase email.
    """

    managers: list[str] = []

    try:
        for firebase_user in auth.list_users().iterate_all():
            custom_claims = firebase_user.custom_claims or {}
            email = (firebase_user.email or "").strip()

            if (
                custom_claims.get("role") == "manager"
                and email
            ):
                managers.append(email)

    except Exception as exc:
        raise ManagerResolutionError(
            "Impossible de résoudre le manager Firebase."
        ) from exc

    if not managers:
        raise ManagerResolutionError(
            "Aucun manager Firebase valide trouvé."
        )

    return sorted(
        managers,
        key=lambda value: value.lower(),
    )[0]

