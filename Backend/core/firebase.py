import firebase_admin
from firebase_admin import credentials, auth

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

SERVICE_ACCOUNT_FILE = BASE_DIR / "firebase_admin_key.json"


if not firebase_admin._apps:
    cred = credentials.Certificate(str(SERVICE_ACCOUNT_FILE))
    firebase_admin.initialize_app(cred)


def verify_token(id_token: str):
    """
    Vérifie le Firebase ID Token envoyé par le frontend.
    """

    decoded_token = auth.verify_id_token(id_token)

    return decoded_token