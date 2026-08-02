from __future__ import annotations

import asyncio
import io
import zipfile
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import select, update

from app.core.config import settings
from app.db.models.answer_passport import AnswerPassport
from app.db.models.membership import Membership
from app.db.models.workspace import Workspace
from app.db.session import AsyncSessionLocal
from app.passport.key_lifecycle import (
    EphemeralSigningProvider,
    InMemoryKeyMetadataRegistry,
    KeyLifecycleService,
)
from app.passport.persistence import (
    PassportPersistenceCoordinator,
    PassportPersistenceStatus,
    TrustMaterial,
)
from app.passport.trust_lifecycle import TrustBundleBuilder
from app.repositories.answer_passports import SQLAlchemyAnswerPassportRepository
from tests.unit.test_passport_persistence_export import issued


async def _persist(workspace_id: UUID) -> str:
    async with AsyncSessionLocal() as session:
        organization_id = await session.scalar(
            select(Workspace.organization_id).where(Workspace.id == workspace_id)
        )
        assert organization_id is not None
        issuance, projected = await issued(organization_id, workspace_id)
        result = await PassportPersistenceCoordinator(
            SQLAlchemyAnswerPassportRepository(session), enabled=True
        ).persist_issued(
            issuance,
            projected,
            organization_id=organization_id,
            workspace_id=workspace_id,
        )
        assert result.status is PassportPersistenceStatus.PERSISTED
        assert result.record is not None
        await session.commit()
        return result.record.passport_id


class ScopedTrustProvider:
    def __init__(self, organization_id: UUID, workspace_id: UUID, material: TrustMaterial) -> None:
        self.organization_id = organization_id
        self.workspace_id = workspace_id
        self.material = material

    async def current(self, organization_id: UUID, workspace_id: UUID) -> TrustMaterial:
        if organization_id != self.organization_id or workspace_id != self.workspace_id:
            raise ValueError("scope_mismatch")
        return self.material


async def _trust_provider(
    workspace_id: UUID, *, bundle_issuer_id: str | None = None
) -> ScopedTrustProvider:
    async with AsyncSessionLocal() as session:
        organization_id = await session.scalar(
            select(Workspace.organization_id).where(Workspace.id == workspace_id)
        )
        assert organization_id is not None
    now = datetime.now(UTC)
    issuer_id = bundle_issuer_id or str(organization_id)
    keys = EphemeralSigningProvider()
    registry = InMemoryKeyMetadataRegistry()
    lifecycle = KeyLifecycleService(registry, keys, clock=lambda: now)
    await keys.create("public-test-key")
    await lifecycle.register_pending(
        issuer_id=issuer_id,
        key_id="public-test-key",
        not_before=now - timedelta(days=1),
        not_after=now + timedelta(days=30),
    )
    await lifecycle.activate(issuer_id, "public-test-key")
    built = await TrustBundleBuilder(clock=lambda: now).build(
        issuer_id=issuer_id,
        records=await registry.list(issuer_id),
        bundle_version=2,
        next_update=now + timedelta(days=1),
        valid_until=now + timedelta(days=2),
    )
    return ScopedTrustProvider(
        organization_id,
        workspace_id,
        TrustMaterial(
            verifier_bundle=built.verifier_bundle,
            lifecycle_bundle=built.bundle,
            bundle_version=built.bundle_version,
            bundle_checksum=built.bundle_checksum,
            trust_mode="unsigned-development",
        ),
    )


def test_authorized_metadata_and_export_are_safe(client, auth_headers, monkeypatch) -> None:
    monkeypatch.setattr(settings, "answer_passport_export_enabled", True)
    passport_id = asyncio.run(_persist(UUID(auth_headers["X-Workspace-ID"])))
    metadata = client.get(f"/api/v1/answer-passports/{passport_id}", headers=auth_headers)
    assert metadata.status_code == 200
    assert metadata.json()["artifact_integrity"] == "VALID"
    assert metadata.json()["status"] == "TRUST_UNAVAILABLE"
    assert "manifest" not in metadata.json()
    assert "signature" not in metadata.json()

    exported = client.get(f"/api/v1/answer-passports/{passport_id}/export", headers=auth_headers)
    assert exported.status_code == 200
    assert exported.headers["cache-control"] == "no-store"
    assert exported.headers["pragma"] == "no-cache"
    assert exported.headers["x-content-type-options"] == "nosniff"
    assert "answer-passport-" in exported.headers["content-disposition"]
    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        assert archive.namelist() == ["export-manifest.json", "passport.json", "passport.sig"]
        assert b"CONFIDENTIAL_EVIDENCE_TEXT" not in exported.content


def test_cross_tenant_lookup_is_non_enumerating(client, auth_headers, monkeypatch) -> None:
    monkeypatch.setattr(settings, "answer_passport_export_enabled", True)
    passport_id = asyncio.run(_persist(UUID(auth_headers["X-Workspace-ID"])))
    second = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"other-{UUID(auth_headers['X-Workspace-ID'])}@example.com",
            "full_name": "Other User",
            "password": "correct-horse-battery-staple",
            "organization_name": "Other Organization",
            "workspace_name": "Other Workspace",
        },
    ).json()
    other_headers = {
        "Authorization": f"Bearer {second['access_token']}",
        "X-Workspace-ID": second["workspace_id"],
    }
    missing = client.get(
        "/api/v1/answer-passports/urn:uuid:00000000-0000-0000-0000-000000000099",
        headers=other_headers,
    )
    denied = client.get(f"/api/v1/answer-passports/{passport_id}", headers=other_headers)
    assert missing.status_code == denied.status_code == 404
    assert missing.json()["error"]["code"] == denied.json()["error"]["code"] == "NOT_FOUND"


def test_corrupt_artifact_and_disabled_feature_fail_closed(
    client, auth_headers, monkeypatch
) -> None:
    workspace_id = UUID(auth_headers["X-Workspace-ID"])
    passport_id = asyncio.run(_persist(workspace_id))
    monkeypatch.setattr(settings, "answer_passport_export_enabled", False)
    disabled = client.get(f"/api/v1/answer-passports/{passport_id}/export", headers=auth_headers)
    assert disabled.status_code == 503

    async def corrupt() -> None:
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(AnswerPassport)
                .where(AnswerPassport.passport_id == passport_id)
                .values(manifest_sha256="0" * 64)
            )
            await session.commit()

    asyncio.run(corrupt())
    monkeypatch.setattr(settings, "answer_passport_export_enabled", True)
    response = client.get(f"/api/v1/answer-passports/{passport_id}/export", headers=auth_headers)
    assert response.status_code == 503
    assert "manifest" not in response.text.lower()


def test_viewer_cannot_export_and_orm_mutation_is_blocked(
    client, auth_headers, monkeypatch
) -> None:
    workspace_id = UUID(auth_headers["X-Workspace-ID"])
    passport_id = asyncio.run(_persist(workspace_id))

    async def make_viewer_and_try_mutation() -> None:
        async with AsyncSessionLocal() as session:
            membership = await session.scalar(
                select(Membership).where(Membership.workspace_id == workspace_id)
            )
            assert membership is not None
            membership.role = "viewer"
            await session.commit()
        async with AsyncSessionLocal() as session:
            record = await session.scalar(
                select(AnswerPassport).where(AnswerPassport.passport_id == passport_id)
            )
            assert record is not None
            record.signature_sha256 = "f" * 64
            with pytest.raises(ValueError, match="immutable"):
                await session.flush()
            await session.rollback()

    asyncio.run(make_viewer_and_try_mutation())
    monkeypatch.setattr(settings, "answer_passport_export_enabled", True)
    metadata = client.get(f"/api/v1/answer-passports/{passport_id}", headers=auth_headers)
    exported = client.get(f"/api/v1/answer-passports/{passport_id}/export", headers=auth_headers)
    assert metadata.status_code == 200
    assert metadata.json()["export_available"] is False
    assert exported.status_code == 403


def test_controlled_trust_bundle_is_scoped_and_public_only(
    client, auth_headers, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "answer_passport_export_enabled", True)
    workspace_id = UUID(auth_headers["X-Workspace-ID"])
    client.app.state.passport_trust_material_provider = asyncio.run(_trust_provider(workspace_id))
    response = client.get("/api/v1/passport-trust-bundles/current", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["bundle_version"] == 2
    assert payload["bundle_checksum"]
    assert payload["verifier_bundle"].startswith('{"generated_at"')
    assert payload["trust_mode"] == "unsigned-development"
    lowered = response.text.lower()
    assert "private_key" not in lowered and "seed" not in lowered and "credential" not in lowered
    del client.app.state.passport_trust_material_provider


def test_trust_bundle_issuer_substitution_is_rejected(client, auth_headers, monkeypatch) -> None:
    monkeypatch.setattr(settings, "answer_passport_export_enabled", True)
    workspace_id = UUID(auth_headers["X-Workspace-ID"])
    client.app.state.passport_trust_material_provider = asyncio.run(
        _trust_provider(workspace_id, bundle_issuer_id=str(UUID(int=42)))
    )
    response = client.get("/api/v1/passport-trust-bundles/current", headers=auth_headers)
    assert response.status_code == 503
    assert "issuer" not in response.text.lower()
    del client.app.state.passport_trust_material_provider


def test_metadata_rejects_cryptographically_invalid_stored_artifact(
    client, auth_headers, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "answer_passport_export_enabled", True)
    workspace_id = UUID(auth_headers["X-Workspace-ID"])
    passport_id = asyncio.run(_persist(workspace_id))
    provider = asyncio.run(_trust_provider(workspace_id))
    provider.material = provider.material.model_copy(update={"verifier_bundle": b'{"bad":true}'})
    client.app.state.passport_trust_material_provider = provider
    response = client.get(f"/api/v1/answer-passports/{passport_id}", headers=auth_headers)
    assert response.status_code == 503
    assert response.json()["error"]["message"] == "Passport artifact is unavailable"
    del client.app.state.passport_trust_material_provider
