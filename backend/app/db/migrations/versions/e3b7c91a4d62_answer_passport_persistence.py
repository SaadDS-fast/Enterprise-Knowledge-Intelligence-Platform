"""add immutable answer passport persistence

Revision ID: e3b7c91a4d62
Revises: d9a1f2c3b4e5
Create Date: 2026-08-02 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e3b7c91a4d62"
down_revision: str | None = "d9a1f2c3b4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "answer_passports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("passport_id", sa.String(64), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("issuer_id", sa.String(200), nullable=False),
        sa.Column("schema_version", sa.String(20), nullable=False),
        sa.Column("envelope_type", sa.String(80), nullable=False),
        sa.Column("signer_key_id", sa.String(200), nullable=False),
        sa.Column("manifest_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("detached_signature", sa.Text(), nullable=False),
        sa.Column("manifest_sha256", sa.String(64), nullable=False),
        sa.Column("signature_sha256", sa.String(64), nullable=False),
        sa.Column("artifact_checksum", sa.String(64), nullable=False),
        sa.Column("scope_fingerprint", sa.String(43), nullable=False),
        sa.Column("answer_hash", sa.String(43), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("correlation_id", sa.String(200), nullable=True),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "schema_version = 'vap-1'", name="ck_answer_passports_schema_version_vap1"
        ),
        sa.CheckConstraint(
            "envelope_type = 'application/vap+jws'",
            name="ck_answer_passports_envelope_type_vap_jws",
        ),
        sa.CheckConstraint(
            "length(manifest_sha256) = 64", name="ck_answer_passports_manifest_sha256_length"
        ),
        sa.CheckConstraint(
            "length(signature_sha256) = 64", name="ck_answer_passports_signature_sha256_length"
        ),
        sa.CheckConstraint(
            "length(artifact_checksum) = 64", name="ck_answer_passports_artifact_checksum_length"
        ),
        sa.CheckConstraint(
            "manifest_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_answer_passports_manifest_sha256_hex",
        ),
        sa.CheckConstraint(
            "signature_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_answer_passports_signature_sha256_hex",
        ),
        sa.CheckConstraint(
            "artifact_checksum ~ '^[0-9a-f]{64}$'",
            name="ck_answer_passports_artifact_checksum_hex",
        ),
        sa.CheckConstraint(
            "idempotency_key ~ '^[0-9a-f]{64}$'",
            name="ck_answer_passports_idempotency_key_hex",
        ),
        sa.CheckConstraint(
            "length(scope_fingerprint) = 43", name="ck_answer_passports_scope_fingerprint_length"
        ),
        sa.CheckConstraint(
            "length(answer_hash) = 43", name="ck_answer_passports_answer_hash_length"
        ),
        sa.CheckConstraint(
            "length(manifest_bytes) <= 1048576", name="ck_answer_passports_manifest_size"
        ),
        sa.CheckConstraint(
            "length(detached_signature) <= 8192", name="ck_answer_passports_signature_size"
        ),
        sa.CheckConstraint(
            "expires_at IS NULL OR expires_at > issued_at",
            name="ck_answer_passports_expiry_after_issue",
        ),
        sa.CheckConstraint("record_version = 1", name="ck_answer_passports_immutable_version"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("passport_id", name="uq_answer_passports_passport_id"),
        sa.UniqueConstraint("idempotency_key", name="uq_answer_passports_idempotency_key"),
    )
    op.create_index(
        op.f("ix_answer_passports_organization_id"), "answer_passports", ["organization_id"]
    )
    op.create_index(op.f("ix_answer_passports_workspace_id"), "answer_passports", ["workspace_id"])
    op.create_index(
        op.f("ix_answer_passports_artifact_checksum"), "answer_passports", ["artifact_checksum"]
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
        CREATE FUNCTION deny_answer_passport_mutation() RETURNS trigger AS $$
        BEGIN RAISE EXCEPTION 'answer passport records are immutable'; END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER trg_answer_passports_immutable
        BEFORE UPDATE OR DELETE ON answer_passports
        FOR EACH ROW EXECUTE FUNCTION deny_answer_passport_mutation();
        """)


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_answer_passports_immutable ON answer_passports")
        op.execute("DROP FUNCTION IF EXISTS deny_answer_passport_mutation()")
    op.drop_index(op.f("ix_answer_passports_artifact_checksum"), table_name="answer_passports")
    op.drop_index(op.f("ix_answer_passports_workspace_id"), table_name="answer_passports")
    op.drop_index(op.f("ix_answer_passports_organization_id"), table_name="answer_passports")
    op.drop_table("answer_passports")
