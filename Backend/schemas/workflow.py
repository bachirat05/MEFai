from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class TypeConge(str, Enum):
    CONGE_ANNUEL = "conge_annuel"
    CONGE_MALADIE = "conge_maladie"
    CONGE_MATERNITE = "conge_maternite"
    CONGE_PATERNITE = "conge_paternite"
    CONGE_SANS_SOLDE = "conge_sans_solde"
    CONGE_FORMATION = "conge_formation"
    AUTRE = "autre"


class DemandeConge(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    employe_id: str = Field(
        min_length=1,
        max_length=50,
    )

    date_debut: date
    date_fin: date

    type_conge: TypeConge

    motif: str = Field(
        min_length=3,
        max_length=500,
    )

    @field_validator("employe_id")
    @classmethod
    def validate_employe_id(
        cls,
        value: str,
    ) -> str:
        value = value.strip()

        if not value:
            raise ValueError(
                "employe_id must not be empty"
            )

        return value

    @field_validator("date_fin")
    @classmethod
    def validate_date_fin(
        cls,
        value: date,
        info,
    ) -> date:
        date_debut = info.data.get(
            "date_debut"
        )

        if (
            date_debut is not None
            and value < date_debut
        ):
            raise ValueError(
                "La date de fin doit être postérieure ou égale à la date de début."
            )

        return value

    @field_validator("motif")
    @classmethod
    def validate_motif(
        cls,
        value: str,
    ) -> str:
        value = value.strip()

        if len(value) < 3:
            raise ValueError(
                "Le motif doit contenir au moins 3 caractères."
            )

        return value


class DemandeCongeResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    demande_id: str
    statut: str
    message: str
    detail: dict | None = None


class LeaveRequestStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statut: Literal["accepted", "rejected"]
