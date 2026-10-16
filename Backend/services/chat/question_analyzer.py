# Fichier pour la détection des questions documentaires, classification des catégories et extraction des sujets
# examine le texte de l'utilisateur pour décider comment le traiter
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

DOCUMENT_VALUE_MARKERS = (
    "code",
    "référence",
    "reference",
    "identifiant",
    "montant",
    "indemnité",
    "indemnite",
    "prime",
    "plafond",
    "maximum",
    "mad",
    "jours",
    "mois",
    "pourcentage",
    "date",
    "durée",
    "duree",
    "limite",
    "ville",
    "ordinateur",
    "informatique",
    "équipement",
    "equipement",
    "matériel",
    "materiel",
    "accessoire",
    "panne",
    "support",
    "vol",
    "perte",
    "renouvellement",
    "renouvelé",
    "renouvele",
    "remboursable",
)

# détermine si la question concerne les documents RH
def is_document_question(self, message: str,) -> bool:
    normalized = message.lower()
    markers = (
        "politique",
        "procédure",
        "procedure",
        "règle",
        "regle",
        "avantage",
        "prime",
        "indemnité",
        "indemnite",
        "formation",
        "certification",
        "congé",
        "conge",
        "télétravail",
        "teletravail",
        "onboarding",
        "intégration",
        "integration",
        "mobilité",
        "mobilite",
        "remboursement",
        "délai",
        "delai",
        "code de référence",
        "code de reference",
        *DOCUMENT_VALUE_MARKERS,
    )
    action_markers = (
        "je veux poser",
        "soumets ma demande",
        "crée une demande",
        "creer une demande",
        "créer une demande",
    )
    return (
        any(marker in normalized for marker in markers)
        and not any(marker in normalized for marker in action_markers)
    )

# identifie une catégorie telle que benefits, leave_policy ou training
def extract_search_subject(
        self,
        message: str,
    ) -> str:
        normalized = message.lower()

        known_subjects = (
            "mobilité interne",
            "mobilite interne",
            "équipement informatique",
            "equipement informatique",
            "matériel informatique",
            "materiel informatique",
            "ordinateur professionnel",
            "formation",
            "certification",
            "congé",
            "conge",
            "télétravail",
            "teletravail",
            "onboarding",
            "intégration",
            "integration",
            "sécurité",
            "securite",
            "confidentialité",
            "confidentialite",
        )

        for subject in known_subjects:
            if subject in normalized:
                return subject

        words = re.findall(
            r"[a-zA-ZÀ-ÿ0-9]{4,}",
            normalized,
        )
        ignored = {
            "quel",
            "quelle",
            "quels",
            "quelles",
            "combien",
            "conditions",
            "politique",
            "document",
            "demande",
            "demandes",
            "reference",
            "référence",
            "montant",
            "code",
            "dans",
            "avec",
            "pour",
            "sont",
            "est",
            "cette",
            "interne",
        }
        subject_words = [
            word
            for word in words
            if word not in ignored
        ]

        return " ".join(
            subject_words[:4]
        )

# extrait le sujet d'une question pour aider les recherches ultérieures
def infer_document_category(
        self,
        message: str,
    ) -> str | None:
        normalized = message.lower()

        if any(
            marker in normalized
            for marker in (
                "mobilité",
                "mobilite",
                "ordinateur",
                "informatique",
                "équipement",
                "equipement",
                "matériel",
                "materiel",
                "accessoire",
                "panne",
                "support",
                "vol",
                "perte",
                "renouvellement",
                "renouvelé",
                "renouvele",
            )
        ):
            return None

        if any(
            marker in normalized
            for marker in (
                "formation",
                "certification",
                "certificat",
                "certif",
            )
        ):
            return "training"

        if any(
            marker in normalized
            for marker in (
                "congé",
                "conge",
                "leave",
            )
        ):
            if any(
                marker in normalized
                for marker in (
                    "étape",
                    "etape",
                    "procédure",
                    "procedure",
                    "validation",
                    "responsable",
                )
            ):
                return "hr_procedure"

            return "leave_policy"

        if any(
            marker in normalized
            for marker in (
                "code",
                "référence",
                "reference",
                "identifiant",
                "montant",
            )
        ):
            return None

        if any(
            marker in normalized
            for marker in (
                "avantage",
                "prime",
                "indemnité",
                "indemnite",
                "benefit",
                "remboursement",
            )
        ):
            return "benefits"

        if any(
            marker in normalized
            for marker in (
                "onboarding",
                "intégration",
                "integration",
            )
        ):
            return "onboarding"

        if any(
            marker in normalized
            for marker in (
                "conformité",
                "conformite",
                "sécurité",
                "securite",
                "confidentialité",
                "confidentialite",
            )
        ):
            return "compliance"

        if any(
            marker in normalized
            for marker in (
                "procédure",
                "procedure",
                "étape",
                "etape",
                "responsable",
                "validation",
            )
        ):
            return "hr_procedure"

        if any(
            marker in normalized
            for marker in (
                "politique",
                "télétravail",
                "teletravail",
            )
        ):
            return "rh_policy"

        return None