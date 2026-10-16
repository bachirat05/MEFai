import asyncio
import os

from schemas.workflow import DemandeConge
from services.workflows.n8n_service import N8nService


async def main():
    service = N8nService(
        webhook_url="http://localhost:5678/webhook-test/conge-test",
        secret_token="test-secret-token-123",
    )

    demande = DemandeConge(
        employe_id="EMP-001",
        date_debut="2026-08-20",
        date_fin="2026-08-25",
        type_conge="conge_annuel",
        motif="Congé annuel",
    )

    result = await service.soumettre_demande_conge(
        demande,
        manager_email=os.environ["TEST_MANAGER_EMAIL"],
    )

    print("\n=== RESULTAT N8N ===")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
