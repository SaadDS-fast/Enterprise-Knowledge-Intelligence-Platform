from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.rate_limit import RateLimited
from app.api.dependencies.tenancy import Tenant
from app.core.config import settings
from app.db.models.answer_passport import AnswerPassport
from app.db.models.role import RoleName
from app.db.session import get_db
from app.exceptions.base import AppError, NotFoundError
from app.exceptions.codes import ErrorCode
from app.passport.persistence import (
    EXPORT_MEDIA_TYPE,
    StoredArtifactError,
    TrustMaterial,
    TrustMaterialProvider,
    build_export_package,
    current_status,
    safe_download_name,
    validate_stored_record,
)
from app.repositories.answer_passports import SQLAlchemyAnswerPassportRepository
from app.security.audit import record_audit_event
from app.security.authorization import can_manage_documents, require_role

router = APIRouter()
trust_router = APIRouter()


class PassportMetadataResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    passport_id: str
    schema_version: str
    issued_at: datetime
    expires_at: datetime | None
    signer_key_id: str
    issuer_id: str
    artifact_integrity: str
    status: str
    freshness: str
    key_lifecycle_status: str
    trust_bundle_version: int | None = None
    trust_bundle_checksum: str | None = None
    export_available: bool


class TrustBundleResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bundle: str
    signature: str | None = None
    trust_mode: str
    bundle_version: int | None = Field(default=None, ge=1)
    bundle_checksum: str | None = None
    bootstrap_notice: str


def _feature_unavailable() -> AppError:
    return AppError(ErrorCode.PROVIDER_UNAVAILABLE, "Answer Passport export is unavailable", 503)


async def _trust(request: Request, tenant: Tenant) -> TrustMaterial | None:
    provider: TrustMaterialProvider | None = getattr(
        request.app.state, "passport_trust_material_provider", None
    )
    if provider is None:
        return None
    try:
        return await provider.current(tenant.organization_id, tenant.workspace_id)
    except Exception:
        return None


async def _record(session: AsyncSession, tenant: Tenant, passport_id: str) -> AnswerPassport | None:
    # A protocol ID is never sufficient: every lookup includes authoritative tenant scope.
    return await SQLAlchemyAnswerPassportRepository(session).get_scoped(
        passport_id, tenant.organization_id, tenant.workspace_id
    )


@router.get("/{passport_id}", response_model=PassportMetadataResponse)
async def metadata(
    passport_id: str,
    request: Request,
    tenant: Tenant,
    _rate: RateLimited,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PassportMetadataResponse:
    if not settings.answer_passport_export_enabled:
        raise _feature_unavailable()
    if len(passport_id) > 64 or not passport_id.startswith("urn:uuid:"):
        raise NotFoundError()
    record = await _record(session, tenant, passport_id)
    if record is None:
        raise NotFoundError()
    try:
        manifest = validate_stored_record(record)
    except StoredArtifactError:
        await record_audit_event(
            session,
            action="PASSPORT_INTEGRITY_FAILED",
            resource_type="answer_passport",
            actor_user_id=tenant.user_id,
            workspace_id=tenant.workspace_id,
            resource_id=passport_id[:80],
        )
        await session.commit()
        raise AppError(
            ErrorCode.PROVIDER_UNAVAILABLE, "Passport artifact is unavailable", 503
        ) from None
    trust = await _trust(request, tenant)
    status, freshness, key_status = current_status(
        record, manifest, now=datetime.now(UTC), trust=trust
    )
    await record_audit_event(
        session,
        action="PASSPORT_METADATA_VIEWED",
        resource_type="answer_passport",
        actor_user_id=tenant.user_id,
        workspace_id=tenant.workspace_id,
        resource_id=passport_id[:80],
        details={"status": status},
    )
    await session.commit()
    return PassportMetadataResponse(
        passport_id=record.passport_id,
        schema_version=record.schema_version,
        issued_at=record.issued_at,
        expires_at=record.expires_at,
        signer_key_id=record.signer_key_id,
        issuer_id=record.issuer_id,
        artifact_integrity="VALID",
        status=status,
        freshness=freshness,
        key_lifecycle_status=key_status,
        trust_bundle_version=trust.bundle_version if trust else None,
        trust_bundle_checksum=trust.bundle_checksum if trust else None,
        export_available=can_manage_documents(tenant.role),
    )


@router.get("/{passport_id}/export")
async def export(
    passport_id: str,
    request: Request,
    tenant: Tenant,
    _rate: RateLimited,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    if not settings.answer_passport_export_enabled:
        raise _feature_unavailable()
    require_role(tenant.role, RoleName.EDITOR)
    if len(passport_id) > 64:
        raise NotFoundError()
    record = await _record(session, tenant, passport_id)
    if record is None:
        raise NotFoundError()
    try:
        manifest = validate_stored_record(record)
        trust = await _trust(request, tenant)
        now = datetime.now(UTC)
        status, freshness, key_status = current_status(record, manifest, now=now, trust=trust)
        if status == "ARTIFACT_INVALID":
            raise StoredArtifactError("signature_invalid")
        if status == "KEY_REVOKED":
            require_role(tenant.role, RoleName.ADMIN)
        package = build_export_package(
            record,
            now=now,
            status=status,
            freshness=freshness,
            key_status=key_status,
            trust=trust,
        )
        filename = safe_download_name(passport_id)
    except StoredArtifactError:
        await record_audit_event(
            session,
            action="PASSPORT_INTEGRITY_FAILED",
            resource_type="answer_passport",
            actor_user_id=tenant.user_id,
            workspace_id=tenant.workspace_id,
            resource_id=passport_id[:80],
        )
        await session.commit()
        raise AppError(
            ErrorCode.PROVIDER_UNAVAILABLE, "Passport artifact is unavailable", 503
        ) from None
    await record_audit_event(
        session,
        action="PASSPORT_EXPORTED",
        resource_type="answer_passport",
        actor_user_id=tenant.user_id,
        workspace_id=tenant.workspace_id,
        resource_id=passport_id[:80],
        details={"status": status, "trust_bundle_included": trust is not None},
    )
    await session.commit()
    return Response(
        package,
        media_type=EXPORT_MEDIA_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
        },
    )


@trust_router.get("/current", response_model=TrustBundleResponse)
async def trust_bundle(
    request: Request,
    tenant: Tenant,
    _rate: RateLimited,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TrustBundleResponse:
    if not settings.answer_passport_export_enabled:
        raise _feature_unavailable()
    require_role(tenant.role, RoleName.EDITOR)
    trust = await _trust(request, tenant)
    if trust is None or trust.lifecycle_bundle is None:
        raise AppError(ErrorCode.PROVIDER_UNAVAILABLE, "Trust material is unavailable", 503)
    await record_audit_event(
        session,
        action="TRUST_BUNDLE_VIEWED",
        resource_type="passport_trust_bundle",
        actor_user_id=tenant.user_id,
        workspace_id=tenant.workspace_id,
        details={"bundle_version": trust.bundle_version, "bundle_checksum": trust.bundle_checksum},
    )
    await session.commit()
    return TrustBundleResponse(
        bundle=trust.lifecycle_bundle.decode("utf-8"),
        signature=trust.lifecycle_signature.decode("ascii") if trust.lifecycle_signature else None,
        trust_mode=trust.trust_mode,
        bundle_version=trust.bundle_version,
        bundle_checksum=trust.bundle_checksum,
        bootstrap_notice="Initial trust requires an independently authenticated channel.",
    )
