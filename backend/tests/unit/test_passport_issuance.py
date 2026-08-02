from __future__ import annotations

import ast
import asyncio
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import ValidationError

from app.core.config import Settings
from app.models.schemas import SearchResponse
from app.passport.canonical import canonicalize
from app.passport.hashing import b64url_encode, content_digest
from app.passport.issuance import (
    ANSWER_NORMALIZATION_VERSION,
    CLAIM_VERIFIER_VERSION,
    EXPORT_POLICY_ID,
    SUPPORT_GATE_VERSION,
    IneligibilityReason,
    IssuanceContext,
    IssuanceStatus,
    PassportIssuanceCoordinator,
    ProjectedCitation,
    ProjectedClaim,
    ProjectionRejected,
    SupportedAnswerProjection,
    eligibility_reason,
    project_search_response,
    response_eligibility_reason,
)
from app.passport.jws import sign_detached
from app.passport.key_lifecycle import (
    EphemeralSigningProvider,
    InMemoryKeyMetadataRegistry,
    KeyLifecycleService,
    LifecyclePassportSigner,
    SigningKeyState,
)
from app.passport.verifier import verify_passport
from app.rag.response_state import (
    CanonicalResponseState,
    ClaimSupport,
    ConfidenceBand,
    ConfidenceComponents,
    ConflictCategory,
    ConflictResult,
    ConflictSide,
    EvidenceDecision,
    PrimaryResponseState,
    ScopeState,
)
from app.services import search_service

ISSUED_AT = datetime(2026, 8, 2, 12, 0, tzinfo=UTC)


class TestSigner:
    def __init__(self, *, fail: bool = False) -> None:
        self.private_key = Ed25519PrivateKey.generate()
        self.key_id = "phase2-test-key"
        self.calls = 0
        self.fail = fail

    async def sign(self, payload: bytes) -> str:
        self.calls += 1
        if self.fail:
            raise RuntimeError("sensitive signer detail")
        return sign_detached(payload, self.private_key, self.key_id)


class BlockingSigner(TestSigner):
    def __init__(self) -> None:
        super().__init__()
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def sign(self, payload: bytes) -> str:
        self.calls += 1
        self.started.set()
        await self.release.wait()
        return sign_detached(payload, self.private_key, self.key_id)


def projection(**updates: object) -> SupportedAnswerProjection:
    citation = ProjectedCitation(
        citation_id="citation-1",
        evidence_id="evidence-1",
        evidence_span=b"Approved evidence span.",
        document_id="document-1",
        document_version="1",
        document_checksum="a" * 64,
        applicability_policy_id=EXPORT_POLICY_ID,
    )
    values: dict[str, object] = {
        "decision": "supported",
        "support_decision_final": True,
        "answer": b"The approved answer.",
        "answer_media_type": "text/plain; charset=utf-8",
        "answer_normalization_version": ANSWER_NORMALIZATION_VERSION,
        "claims": (
            ProjectedClaim(
                claim_id="claim-1",
                normalized_text="The approved answer.",
                verified=True,
                citations=(citation,),
            ),
        ),
        "tenant_id": "tenant-a",
        "workspace_id": "workspace-a",
        "audience_policy_id": EXPORT_POLICY_ID,
        "export_policy_id": EXPORT_POLICY_ID,
        "support_gate_version": SUPPORT_GATE_VERSION,
        "claim_verifier_version": CLAIM_VERIFIER_VERSION,
        "retrieval_configuration": canonicalize({"top_k": 20, "retry_budget": 0}),
        "generation_provider_alias": "extractive",
        "approved_model_digest": None,
        "completed_at": ISSUED_AT,
        "correlation_id": "request-1",
    }
    values.update(updates)
    return SupportedAnswerProjection.model_validate(values)


def trust_bundle(signer: TestSigner) -> bytes:
    public_key = signer.private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return canonicalize(
        {
            "schema_version": "vap-trust-1",
            "generated_at": "2026-08-02T12:00:00Z",
            "keys": [
                {
                    "key_id": signer.key_id,
                    "algorithm": "EdDSA",
                    "public_key": b64url_encode(public_key),
                    "status": "trusted",
                    "not_before": "2026-01-01T00:00:00Z",
                    "not_after": "2028-01-01T00:00:00Z",
                    "revoked_at": None,
                }
            ],
        }
    )


@pytest.mark.asyncio
async def test_lifecycle_signer_selects_active_key_server_side() -> None:
    provider = EphemeralSigningProvider()
    registry = InMemoryKeyMetadataRegistry()
    lifecycle = KeyLifecycleService(registry, provider, clock=lambda: ISSUED_AT)
    await provider.create("active-server-key")
    await lifecycle.register_pending(
        issuer_id="issuer-a",
        key_id="active-server-key",
        not_before=datetime(2026, 1, 1, tzinfo=UTC),
        not_after=datetime(2027, 1, 1, tzinfo=UTC),
    )
    await lifecycle.activate("issuer-a", "active-server-key")
    signer = LifecyclePassportSigner("issuer-a", lifecycle)
    coordinator = PassportIssuanceCoordinator(enabled=True, signer=signer)
    result = await coordinator.issue(projection(), context=IssuanceContext())
    assert result.status is IssuanceStatus.ISSUED
    assert result.signer_key_id == "active-server-key"
    assert b'"key_id":"active-server-key"' in (result.manifest or b"")
    await lifecycle.transition("issuer-a", "active-server-key", SigningKeyState.RETIRED)
    unavailable = await PassportIssuanceCoordinator(enabled=True, signer=signer).issue(
        projection(), context=IssuanceContext()
    )
    assert unavailable.status is IssuanceStatus.SIGNER_UNAVAILABLE
    assert unavailable.manifest is None and unavailable.detached_signature is None


def canonical_state(
    primary: PrimaryResponseState = PrimaryResponseState.SUPPORTED,
) -> CanonicalResponseState:
    if primary == PrimaryResponseState.CONFLICTING_EVIDENCE:
        return CanonicalResponseState(
            primary_state=primary,
            answer=None,
            claims=[],
            citation_ids=["citation-1", "citation-2"],
            citation_document_ids={"citation-1": "doc-1", "citation-2": "doc-2"},
            evidence_decision=EvidenceDecision.CONFLICTING,
            conflict=ConflictResult(
                category=ConflictCategory.VALUE_CONFLICT,
                unresolved=True,
                material=True,
                sides=[
                    ConflictSide(claim_id="side-1", text="A", citation_ids=["citation-1"]),
                    ConflictSide(claim_id="side-2", text="B", citation_ids=["citation-2"]),
                ],
            ),
            confidence=ConfidenceComponents(final=ConfidenceBand.LOW),
            scope=ScopeState(authorized_document_ids=["doc-1", "doc-2"]),
            user_message="Authorized sources contain conflicting information.",
        )
    if primary != PrimaryResponseState.SUPPORTED:
        return CanonicalResponseState(
            primary_state=primary,
            evidence_decision=EvidenceDecision.ABSENT,
            user_message="I can’t provide a supported answer from the available evidence.",
        )
    return CanonicalResponseState(
        primary_state=primary,
        answer="Supported answer",
        claims=[ClaimSupport(claim_id="claim-1", text="Supported answer", citation_ids=["c1"])],
        citation_ids=["c1"],
        citation_document_ids={"c1": "doc-1"},
        evidence_decision=EvidenceDecision.SUFFICIENT,
        confidence=ConfidenceComponents(final=ConfidenceBand.HIGH),
        scope=ScopeState(authorized_document_ids=["doc-1"]),
        user_message="Supported answer",
    )


def response_for(primary: PrimaryResponseState) -> SearchResponse:
    state = canonical_state(primary)
    citations = (
        [
            {
                "citation_id": item,
                "document_id": document,
                "chunk_id": str(UUID(int=index + 1)),
                "excerpt": "evidence",
            }
            for index, (item, document) in enumerate(state.citation_document_ids.items())
        ]
        if primary in {PrimaryResponseState.SUPPORTED, PrimaryResponseState.CONFLICTING_EVIDENCE}
        else []
    )
    return SearchResponse(
        answer=state.user_message,
        evidence=[],
        sufficient_evidence=primary == PrimaryResponseState.SUPPORTED,
        abstained=primary != PrimaryResponseState.SUPPORTED,
        citations=citations,
        conflicts=[{"status": "CONFIRMED_CONFLICT"}]
        if primary == PrimaryResponseState.CONFLICTING_EVIDENCE
        else [],
        active_document_scope=[
            {"document_id": document} for document in state.citation_document_ids.values()
        ],
        response_state=state,
    )


class FakeRows:
    def __init__(self, rows: list[Any]) -> None:
        self.rows = rows

    def all(self) -> list[Any]:
        return self.rows


class FakeSession:
    def __init__(self, *, workspace_id: UUID, chunk_id: UUID) -> None:
        self.workspace_id = workspace_id
        self.workspace = SimpleNamespace(organization_id=UUID(int=90))
        self.row = SimpleNamespace(
            Chunk=SimpleNamespace(id=chunk_id),
            Document=SimpleNamespace(id=UUID(int=70)),
            DocumentVersion=SimpleNamespace(version_number=3, checksum_sha256="b" * 64),
        )

    async def get(self, model: object, identifier: UUID) -> Any:
        del model
        return self.workspace if identifier == self.workspace_id else None

    async def execute(self, statement: object) -> FakeRows:
        del statement
        return FakeRows([self.row])


@pytest.mark.asyncio
async def test_projection_adapter_uses_final_displayed_and_server_derived_data() -> None:
    workspace_id = UUID(int=50)
    chunk_id = UUID(int=60)
    document_id = UUID(int=70)
    state = CanonicalResponseState(
        primary_state=PrimaryResponseState.SUPPORTED,
        answer="  Final supported answer.  ",
        claims=[
            ClaimSupport(
                claim_id="claim-1",
                text="Final   supported answer.",
                citation_ids=["citation-1"],
            )
        ],
        citation_ids=["citation-1"],
        citation_document_ids={"citation-1": str(document_id)},
        evidence_decision=EvidenceDecision.SUFFICIENT,
        confidence=ConfidenceComponents(final=ConfidenceBand.HIGH),
        scope=ScopeState(authorized_document_ids=[str(document_id)]),
        user_message="  Final supported answer.  ",
    )
    response = SearchResponse(
        answer=state.user_message,
        evidence=[],
        sufficient_evidence=True,
        abstained=False,
        citations=[
            {
                "citation_id": "citation-1",
                "chunk_id": str(chunk_id),
                "document_id": str(document_id),
                "excerpt": "Displayed verified span.",
            }
        ],
        active_document_scope=[{"document_id": str(document_id)}],
        response_state=state,
        request_id="request-safe",
        generation_provider="ollama",
        generation_model="approved-local-model",
        generation_used=True,
        generation_verification="verified",
        claim_verification_passed=True,
    )
    session = FakeSession(workspace_id=workspace_id, chunk_id=chunk_id)
    first = await project_search_response(
        session,  # type: ignore[arg-type]
        response=response,
        workspace_id=workspace_id,
        completed_at=ISSUED_AT,
        retrieval_configuration={"top_k": 20, "retry_budget": 0},
    )
    second = await project_search_response(
        session,  # type: ignore[arg-type]
        response=response,
        workspace_id=workspace_id,
        completed_at=ISSUED_AT,
        retrieval_configuration={"retry_budget": 0, "top_k": 20},
    )
    assert first == second
    assert first.tenant_id == str(UUID(int=90))
    assert first.workspace_id == str(workspace_id)
    assert first.answer == b"  Final supported answer.  "
    assert first.claims[0].normalized_text == "Final supported answer."
    assert first.claims[0].citations[0].evidence_span == b"Displayed verified span."
    assert first.claims[0].citations[0].document_version == "3"
    assert first.claims[0].citations[0].document_checksum == "b" * 64
    assert first.generation_provider_alias == "ollama"
    assert first.approved_model_digest == content_digest("CONFIG", b"approved-local-model")
    dumped = first.model_dump()
    assert not ({"prompt", "score", "private_key", "acl", "token"} & set(dumped))

    response.citations[0]["document_id"] = str(UUID(int=71))
    with pytest.raises(ProjectionRejected, match="INCOMPLETE_CITATION_MAPPING"):
        await project_search_response(
            session,  # type: ignore[arg-type]
            response=response,
            workspace_id=workspace_id,
            completed_at=ISSUED_AT,
            retrieval_configuration={"top_k": 20},
        )


def test_projection_is_frozen_and_rejects_prohibited_or_malformed_fields() -> None:
    item = projection()
    with pytest.raises(ValidationError):
        item.workspace_id = "workspace-b"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        SupportedAnswerProjection.model_validate(
            {**item.model_dump(), "prompt": "secret", "workspace_id": "workspace-b"}
        )
    with pytest.raises(ValidationError):
        projection(claims=(item.claims[0], item.claims[0]))
    with pytest.raises(ValidationError):
        ProjectedCitation.model_validate(
            {**item.claims[0].citations[0].model_dump(), "document_checksum": "bad"}
        )


def test_feature_flag_defaults_disabled() -> None:
    assert Settings(_env_file=None).answer_passport_enabled is False


def test_integration_module_has_no_retrieval_generation_or_network_dependency() -> None:
    source = Path(__file__).parents[2] / "app" / "passport" / "issuance.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    forbidden_app = {"agents", "integrations", "llm", "rag", "services"}
    forbidden_external = {"httpx", "requests", "socket", "urllib"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            parts = node.module.split(".")
            assert not (len(parts) > 1 and parts[0] == "app" and parts[1] in forbidden_app)
            assert parts[0] not in forbidden_external
        if isinstance(node, ast.Import):
            roots = {alias.name.split(".")[0] for alias in node.names}
            assert roots.isdisjoint(forbidden_external)


@pytest.mark.asyncio
async def test_generated_passport_verifies_offline_and_binds_scope() -> None:
    signer = TestSigner()
    coordinator = PassportIssuanceCoordinator(
        enabled=True,
        signer=signer,
        clock=lambda: ISSUED_AT,
        identifier=lambda: UUID("12345678-1234-5678-9234-567812345678"),
    )
    result = await coordinator.issue(projection(), context=IssuanceContext())
    assert result.status == IssuanceStatus.ISSUED
    assert result.manifest and result.detached_signature
    verified = verify_passport(
        result.manifest,
        result.detached_signature,
        trust_bundle(signer),
        answer_bytes=b"The approved answer.",
        at=ISSUED_AT,
    )
    assert verified.status == "VERIFIED_WITHOUT_SNAPSHOT"
    wrong_scope = verify_passport(
        result.manifest,
        result.detached_signature,
        trust_bundle(signer),
        expected_scope_fingerprint=content_digest("SCOPE", b"another tenant"),
        at=ISSUED_AT,
    )
    assert wrong_scope.status == "CONTENT_MODIFIED"


@pytest.mark.asyncio
async def test_disabled_and_missing_signer_fail_closed_without_signing() -> None:
    signer = TestSigner()
    disabled = await PassportIssuanceCoordinator(enabled=False, signer=signer).issue(
        projection(), context=IssuanceContext()
    )
    unavailable = await PassportIssuanceCoordinator(enabled=True).issue(
        projection(), context=IssuanceContext()
    )
    assert disabled.status == IssuanceStatus.NOT_REQUESTED_OR_DISABLED
    assert unavailable.status == IssuanceStatus.SIGNER_UNAVAILABLE
    assert signer.calls == 0
    assert unavailable.manifest is None and unavailable.detached_signature is None


@pytest.mark.asyncio
async def test_concurrent_duplicate_hooks_issue_exactly_once() -> None:
    signer = TestSigner()
    coordinator = PassportIssuanceCoordinator(enabled=True, signer=signer)
    context = IssuanceContext()
    first, second = await asyncio.gather(
        coordinator.issue(projection(), context=context),
        coordinator.issue(projection(), context=context),
    )
    assert first == second
    assert first.status == IssuanceStatus.ISSUED
    assert signer.calls == 1


@pytest.mark.asyncio
async def test_signer_failure_is_safe_cached_and_does_not_leak() -> None:
    signer = TestSigner(fail=True)
    coordinator = PassportIssuanceCoordinator(enabled=True, signer=signer)
    context = IssuanceContext()
    first = await coordinator.issue(projection(), context=context)
    second = await coordinator.issue(projection(), context=context)
    assert first == second
    assert first.status == IssuanceStatus.FAILED
    assert first.manifest is None and first.detached_signature is None
    assert "sensitive" not in first.model_dump_json()
    assert signer.calls == 1


@pytest.mark.asyncio
async def test_cancellation_leaves_no_artifact_and_prevents_reissue() -> None:
    signer = BlockingSigner()
    coordinator = PassportIssuanceCoordinator(enabled=True, signer=signer)
    context = IssuanceContext()
    task = asyncio.create_task(coordinator.issue(projection(), context=context))
    await signer.started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    result = await coordinator.issue(projection(), context=context)
    assert result.status == IssuanceStatus.FAILED
    assert result.manifest is None and result.detached_signature is None
    assert signer.calls == 1


@pytest.mark.parametrize(
    ("primary", "reason"),
    [
        (PrimaryResponseState.INSUFFICIENT_EVIDENCE, IneligibilityReason.RESULT_NOT_SUPPORTED),
        (PrimaryResponseState.PROCESSING_FAILED, IneligibilityReason.RESULT_NOT_SUPPORTED),
        (PrimaryResponseState.CANCELLED, IneligibilityReason.RESULT_NOT_SUPPORTED),
        (PrimaryResponseState.CONFLICTING_EVIDENCE, IneligibilityReason.CONFLICT_NOT_ELIGIBLE),
    ],
)
def test_non_supported_final_states_are_ineligible(
    primary: PrimaryResponseState, reason: IneligibilityReason
) -> None:
    response = response_for(primary)
    before = response.model_dump()
    assert response_eligibility_reason(response) == reason
    assert response.model_dump() == before


def test_supported_final_state_is_eligible_and_scope_is_required() -> None:
    response = response_for(PrimaryResponseState.SUPPORTED)
    assert response_eligibility_reason(response) is None


@pytest.mark.asyncio
async def test_projection_adapter_rejects_missing_server_scope() -> None:
    response = response_for(PrimaryResponseState.SUPPORTED)
    session = FakeSession(workspace_id=UUID(int=2), chunk_id=UUID(int=1))
    with pytest.raises(ProjectionRejected, match="MISSING_SCOPE"):
        await project_search_response(
            session,  # type: ignore[arg-type]
            response=response,
            workspace_id=UUID(int=3),
            completed_at=ISSUED_AT,
            retrieval_configuration={"top_k": 20},
        )


def test_eligibility_feature_and_signer_guards() -> None:
    signer = TestSigner()
    assert eligibility_reason(projection(), enabled=False, signer=signer) == "FEATURE_DISABLED"
    assert eligibility_reason(projection(), enabled=True, signer=None) == "SIGNER_UNAVAILABLE"
    assert eligibility_reason(None, enabled=True, signer=None) == "SIGNER_UNAVAILABLE"
    assert eligibility_reason(None, enabled=True, signer=signer) == "RESULT_NOT_SUPPORTED"
    assert eligibility_reason(projection(), enabled=True, signer=signer) is None


@pytest.mark.asyncio
async def test_audit_sink_receives_only_minimal_safe_metadata() -> None:
    events: list[dict[str, str | None]] = []

    async def sink(event: dict[str, str | None]) -> None:
        events.append(event)

    signer = TestSigner()
    result = await PassportIssuanceCoordinator(
        enabled=True, signer=signer, audit_sink=sink, clock=lambda: ISSUED_AT
    ).issue(projection(), context=IssuanceContext())
    assert result.status == IssuanceStatus.ISSUED
    assert set(events[0]) == {
        "event_type",
        "passport_id",
        "schema_version",
        "issuance_status",
        "scope_fingerprint",
        "signer_key_id",
        "correlation_id",
        "timestamp",
    }
    assert "The approved answer." not in str(events)
    assert "Approved evidence span." not in str(events)


@pytest.mark.asyncio
async def test_disabled_production_hook_preserves_answer_and_runs_lifecycle_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    answer = response_for(PrimaryResponseState.SUPPORTED)
    before = answer.model_dump()
    lifecycle_calls = 0
    signer = TestSigner()

    async def finalized_lifecycle(*args: object, **kwargs: object) -> SearchResponse:
        nonlocal lifecycle_calls
        del args, kwargs
        lifecycle_calls += 1
        return answer

    monkeypatch.setattr(search_service, "_search_and_answer", finalized_lifecycle)
    result = await search_service.search_and_answer(
        object(),  # type: ignore[arg-type]
        workspace_id=UUID(int=1),
        query="already finalized",
        passport_coordinator=PassportIssuanceCoordinator(enabled=False, signer=signer),
    )
    assert result.model_dump() == before
    assert lifecycle_calls == 1
    assert signer.calls == 0
