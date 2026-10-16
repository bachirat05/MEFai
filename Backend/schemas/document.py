from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DocumentCategory(str, Enum):
    RH_POLICY = "rh_policy"
    HR_PROCEDURE = "hr_procedure"
    LEAVE_POLICY = "leave_policy"
    BENEFITS = "benefits"
    TRAINING = "training"
    ONBOARDING = "onboarding"
    COMPLIANCE = "compliance"
    OTHER = "other"


class DocumentSource(str, Enum):
    INTERNAL_WIKI = "internal_wiki"
    PDF_UPLOAD = "pdf_upload"
    HR_SYSTEM = "hr_system"
    MANUAL = "manual"
    EXTERNAL = "external"


class DocumentMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: DocumentCategory
    source: DocumentSource
    department: str = Field(min_length=1, max_length=100)
    tags: list[str] = Field(default_factory=list)
    filename: str | None = None
    document_type: str | None = None
    chunk_index: int | None = None
    chunk_count: int | None = None
    effective_date: str | None = None
    author: str | None = None
    version: str = "1.0.0"

    @field_validator("department")
    @classmethod
    def validate_department(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Department must not be empty")
        return v.strip()


class DocumentIngestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1)
    metadata: DocumentMetadata
    document_id: str | None = None

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Document content must not be empty")
        return v.strip()


class DocumentSearchQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)
    category: DocumentCategory | None = None
    department: str | None = None
    tags: list[str] = Field(default_factory=list)
    top_k: int = Field(default=5, ge=1, le=50)
    similarity_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class DocumentSearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    content: str
    metadata: DocumentMetadata
    score: float


class DocumentSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    results: list[DocumentSearchResult]
    total_found: int
    returned_count: int
