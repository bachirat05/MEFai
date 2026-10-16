from __future__ import annotations

import sys

import firebase_admin
from firebase_admin import credentials, auth


# =========================================================
# FIREBASE ADMIN INITIALIZATION
# =========================================================

if not firebase_admin._apps:
    cred = credentials.Certificate(
        "Backend/app/firebase_admin_key.json"
    )

    firebase_admin.initialize_app(cred)


# =========================================================
# GET EMAIL
# =========================================================

if len(sys.argv) != 2:
    print("Usage:")
    print("python Backend/set_admin.py email@example.com")
    sys.exit(1)


email = sys.argv[1]


# =========================================================
# SET ADMIN ROLE
# =========================================================

try:
    user = auth.get_user_by_email(email)

    auth.set_custom_user_claims(
        user.uid,
        {
            "role": "admin"
        },
    )

    print("========================================")
    print("✅ Admin role assigned successfully")
    print("========================================")
    print(f"Email : {user.email}")
    print(f"UID   : {user.uid}")
    print("Role  : admin")

except auth.UserNotFoundError:
    print(
        f"❌ Aucun utilisateur Firebase trouvé avec l'email : {email}"
    )

except Exception as exc:
    print(f"❌ Error: {exc}")