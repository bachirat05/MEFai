from __future__ import annotations

from pathlib import Path

import firebase_admin
from firebase_admin import auth, credentials


BASE_DIR = Path(__file__).resolve().parent

SERVICE_ACCOUNT_PATH = (
    BASE_DIR / "app" / "firebase_admin_key.json"
)


if not firebase_admin._apps:
    cred = credentials.Certificate(
        str(SERVICE_ACCOUNT_PATH)
    )

    firebase_admin.initialize_app(
        cred
    )


EMAIL = "bachirat.salma@etu.uae.ac.ma"


user = auth.get_user_by_email(
    EMAIL
)


auth.set_custom_user_claims(
    user.uid,
    {
        "role": "manager",
    },
)


print(
    f"Role manager ajouté à {EMAIL}"
)