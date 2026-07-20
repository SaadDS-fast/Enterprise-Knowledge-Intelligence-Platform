from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    message: str


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=12, max_length=128)
    organization_name: str = Field(default="My Organization", min_length=2, max_length=160)
    workspace_name: str = Field(default="General", min_length=2, max_length=160)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(ORMModel):
    id: UUID
    email: EmailStr
    full_name: str
    is_active: bool
    is_superuser: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105
    expires_in: int
    user: UserRead
    workspace_id: UUID


class WorkspaceRead(ORMModel):
    id: UUID
    organization_id: UUID
    name: str
    slug: str


class DocumentRead(ORMModel):
    id: UUID
    workspace_id: UUID
    title: str
    status: str
    description: str | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class DocumentVersionRead(ORMModel):
    id: UUID
    document_id: UUID
    version_number: int
    filename: str
    mime_type: str
    size_bytes: int
    checksum_sha256: str
    created_at: datetime


class UploadResponse(BaseModel):
    document: DocumentRead
    version: DocumentVersionRead
    job_id: UUID
    status: str


class JobRead(ORMModel):
    id: UUID
    workspace_id: UUID
    document_version_id: UUID
    status: str
    stage: str
    error_message: str | None
    result_json: dict
    created_at: datetime
    updated_at: datetime


class EvidenceItem(BaseModel):
    chunk_id: UUID
    document_id: UUID
    document_title: str
    content: str
    score: float = Field(ge=0.0, le=1.0)
    metadata: dict = Field(default_factory=dict)


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=4000)
    top_k: int | None = Field(default=None, ge=1, le=50)
    document_ids: list[UUID] | None = None


class SearchResponse(BaseModel):
    answer: str
    evidence: list[EvidenceItem]
    sufficient_evidence: bool
    abstained: bool
    request_id: str | None = None
    retrieval_diagnosis: dict = Field(default_factory=dict)


class ResearchRequest(BaseModel):
    question: str = Field(min_length=5, max_length=4000)


class ResearchRead(ORMModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    question: str
    status: str
    report_markdown: str | None
    result_json: dict
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class EvaluationCase(BaseModel):
    question: str = Field(min_length=2)
    expected_answer: str = Field(min_length=1)


class EvaluationRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    cases: list[EvaluationCase] = Field(min_length=1, max_length=100)


class EvaluationRead(ORMModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    name: str
    status: str
    metrics_json: dict
    config_json: dict
    created_at: datetime
    updated_at: datetime


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
