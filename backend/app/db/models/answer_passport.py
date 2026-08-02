from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class AnswerPassport(UUIDPrimaryKeyMixin, Base):
    """Append-only signed artifact. Application code exposes no mutation or delete operation."""

    __tablename__ = "answer_passports"
    __table_args__ = (
        UniqueConstraint("passport_id", name="uq_answer_passports_passport_id"),
        UniqueConstraint("idempotency_key", name="uq_answer_passports_idempotency_key"),
        CheckConstraint("schema_version = 'vap-1'", name="schema_version_vap1"),
        CheckConstraint("envelope_type = 'application/vap+jws'", name="envelope_type_vap_jws"),
        CheckConstraint("length(manifest_sha256) = 64", name="manifest_sha256_length"),
        CheckConstraint("length(signature_sha256) = 64", name="signature_sha256_length"),
        CheckConstraint("length(artifact_checksum) = 64", name="artifact_checksum_length"),
        CheckConstraint(
            "manifest_sha256 ~ '^[0-9a-f]{64}$'", name="manifest_sha256_hex"
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "signature_sha256 ~ '^[0-9a-f]{64}$'", name="signature_sha256_hex"
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "artifact_checksum ~ '^[0-9a-f]{64}$'", name="artifact_checksum_hex"
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "idempotency_key ~ '^[0-9a-f]{64}$'", name="idempotency_key_hex"
        ).ddl_if(dialect="postgresql"),
        CheckConstraint("length(scope_fingerprint) = 43", name="scope_fingerprint_length"),
        CheckConstraint("length(answer_hash) = 43", name="answer_hash_length"),
        CheckConstraint("length(manifest_bytes) <= 1048576", name="manifest_size"),
        CheckConstraint("length(detached_signature) <= 8192", name="signature_size"),
        CheckConstraint("expires_at IS NULL OR expires_at > issued_at", name="expiry_after_issue"),
        CheckConstraint("record_version = 1", name="immutable_version"),
    )

    passport_id: Mapped[str] = mapped_column(String(64), nullable=False)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    issuer_id: Mapped[str] = mapped_column(String(200), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(20), nullable=False)
    envelope_type: Mapped[str] = mapped_column(String(80), nullable=False)
    signer_key_id: Mapped[str] = mapped_column(String(200), nullable=False)
    manifest_bytes: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    detached_signature: Mapped[str] = mapped_column(Text, nullable=False)
    manifest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    signature_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    scope_fingerprint: Mapped[str] = mapped_column(String(43), nullable=False)
    answer_hash: Mapped[str] = mapped_column(String(43), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    correlation_id: Mapped[str | None] = mapped_column(String(200))
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    record_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


def _deny_mutation(_mapper: object, _connection: object, _target: AnswerPassport) -> None:
    raise ValueError("answer_passport_records_are_immutable")


event.listen(AnswerPassport, "before_update", _deny_mutation)
event.listen(AnswerPassport, "before_delete", _deny_mutation)
