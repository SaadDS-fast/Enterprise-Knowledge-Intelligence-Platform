from __future__ import annotations

import ast
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.passport.canonical import CanonicalizationError, canonicalize, parse_json_strict
from app.passport.hashing import b64url_encode, content_digest
from app.passport.jws import sign_detached
from app.passport.verifier import verify_passport

ANSWER = b"Travel requires manager approval."
# Ephemeral process-local test key: never serialized, logged, or written to disk.
PRIVATE_KEY = Ed25519PrivateKey.generate()
PUBLIC_KEY = PRIVATE_KEY.public_key().public_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PublicFormat.Raw,
)


def manifest(*, not_after: str | None = "2027-01-01T00:00:00Z") -> dict[str, object]:
    return {
        "schema_version": "vap-1",
        "certificate_id": "urn:uuid:12345678-1234-5678-9234-567812345678",
        "answer": {
            "media_type": "text/plain; charset=utf-8",
            "sha256": content_digest("ANSWER", ANSWER),
        },
        "claims": [
            {
                "claim_id": "claim-1",
                "normalized_sha256": content_digest("CLAIM", b"travel requires manager approval"),
                "citations": [
                    {
                        "evidence_id": "evidence-1",
                        "evidence_span_sha256": content_digest(
                            "EVIDENCE_SPAN", b"Manager approval is required for travel."
                        ),
                        "document_id": "document-1",
                        "document_version": "1",
                        "document_sha256": content_digest("DOCUMENT", b"document bytes"),
                        "scope_fingerprint": content_digest("SCOPE", b"tenant/workspace"),
                        "applicability": {"policy_id": "travel-policy"},
                    }
                ],
            }
        ],
        "scope": {
            "tenant_workspace_fingerprint": content_digest("SCOPE", b"tenant/workspace"),
            "audience": "audit-team",
        },
        "assurance": {
            "support_gate_version": "static-v1",
            "verifier_version": "vap-core-1",
            "retrieval_configuration_sha256": content_digest("CONFIG", b"config"),
            "generation_provider_alias": "extractive",
            "approved_model_digest": None,
        },
        "issued_at": "2026-08-01T00:00:00Z",
        "freshness": {"policy_id": "annual", "not_after": not_after},
        "signing": {"algorithm": "EdDSA", "key_id": "test-key-1"},
    }


def trust_bundle(
    *,
    status: str = "trusted",
    key_id: str = "test-key-1",
    public_key: bytes = PUBLIC_KEY,
    not_before: str = "2026-01-01T00:00:00Z",
    not_after: str = "2029-01-01T00:00:00Z",
    schema_version: str = "vap-trust-1",
) -> bytes:
    return canonicalize(
        {
            "schema_version": schema_version,
            "generated_at": "2026-08-01T00:00:00Z",
            "keys": [
                {
                    "key_id": key_id,
                    "algorithm": "EdDSA",
                    "public_key": b64url_encode(public_key),
                    "status": status,
                    "not_before": not_before,
                    "not_after": not_after,
                    "revoked_at": "2026-08-02T00:00:00Z" if status == "revoked" else None,
                }
            ],
        }
    )


def signed_artifact(data: dict[str, object] | None = None) -> tuple[bytes, str]:
    payload = canonicalize(data or manifest())
    return payload, sign_detached(payload, PRIVATE_KEY, "test-key-1")


def test_canonicalization_golden_vector_and_strict_parser() -> None:
    value = {"z": [True, None, "é"], "a": {"b": 2, "a": 1}}
    assert canonicalize(value) == '{"a":{"a":1,"b":2},"z":[true,null,"é"]}'.encode()
    with pytest.raises(CanonicalizationError, match="duplicate_json_key"):
        parse_json_strict(b'{"answer":1,"answer":2}')
    with pytest.raises(CanonicalizationError, match="floating_point"):
        canonicalize({"unsupported": 1.5})


def test_canonicalization_uses_rfc_8785_utf16_property_order() -> None:
    # U+1F600 sorts before U+E000 by UTF-16 code unit (D83D < E000), but after it by code point.
    assert canonicalize({"\ue000": 1, "😀": 2}) == '{"😀":2,"\ue000":1}'.encode()


def test_domain_separation_changes_digest() -> None:
    assert content_digest("ANSWER", b"same") != content_digest("CLAIM", b"same")
    with pytest.raises(ValueError, match="unsupported_hash_domain"):
        content_digest("UNKNOWN", b"same")


def test_passport_package_has_no_forbidden_runtime_dependencies() -> None:
    package = Path(__file__).parents[2] / "app" / "passport"
    forbidden_app = {
        "agents",
        "api",
        "db",
        "evaluation",
        "ingestion",
        "integrations",
        "llm",
        "rag",
        "repositories",
        "services",
    }
    forbidden_external = {"httpx", "requests", "socket", "urllib"}
    for source in package.glob("*.py"):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                parts = node.module.split(".")
                assert not (len(parts) > 1 and parts[0] == "app" and parts[1] in forbidden_app)
                assert parts[0] not in forbidden_external
            if isinstance(node, ast.Import):
                imported_roots = {alias.name.split(".")[0] for alias in node.names}
                assert imported_roots.isdisjoint(forbidden_external)


def test_valid_artifact_and_answer_verify_deterministically() -> None:
    payload, signature = signed_artifact()
    result = verify_passport(
        payload,
        signature,
        trust_bundle(),
        answer_bytes=ANSWER,
        at=datetime(2026, 8, 1, tzinfo=UTC),
    )
    assert result.overall == "valid"
    assert result.signature_valid is True
    assert result.content_integrity == "valid"
    assert result.freshness == "fresh"
    assert result.errors == []


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    [
        (
            lambda item: item["answer"].update({"sha256": content_digest("ANSWER", b"changed")}),
            "signature_verification_failed",
        ),
        (
            lambda item: item["claims"][0].update({"claim_id": "changed"}),
            "signature_verification_failed",
        ),
        (
            lambda item: item["claims"][0]["citations"][0].update({"document_version": "2"}),
            "signature_verification_failed",
        ),
        (
            lambda item: item["claims"][0]["citations"][0].update(
                {"evidence_span_sha256": content_digest("EVIDENCE_SPAN", b"changed")}
            ),
            "signature_verification_failed",
        ),
    ],
)
def test_signed_manifest_mutations_are_detected(mutation, expected_error: str) -> None:
    original, signature = signed_artifact()
    changed = json.loads(original)
    mutation(changed)
    result = verify_passport(canonicalize(changed), signature, trust_bundle())
    assert result.overall == "invalid"
    assert expected_error in result.errors


def test_answer_mutation_is_reported_separately() -> None:
    payload, signature = signed_artifact()
    result = verify_passport(payload, signature, trust_bundle(), answer_bytes=b"modified answer")
    assert result.signature_valid is True
    assert result.content_integrity == "invalid"
    assert result.errors == ["answer_hash_mismatch"]


def test_signature_mutation_is_detected() -> None:
    payload, signature = signed_artifact()
    replacement = "A" if signature[-1] != "A" else "B"
    result = verify_passport(payload, signature[:-1] + replacement, trust_bundle())
    assert result.signature_valid is False
    assert result.errors == ["signature_verification_failed"]


def test_protected_key_id_must_match_manifest() -> None:
    payload, _ = signed_artifact()
    signature = sign_detached(payload, PRIVATE_KEY, "substituted-key")
    result = verify_passport(payload, signature, trust_bundle())
    assert result.signature_valid is False
    assert result.errors == ["signature_key_id_does_not_match_manifest"]


def test_noncanonical_manifest_is_rejected_before_signature() -> None:
    data = manifest()
    noncanonical = json.dumps(data, indent=2).encode()
    signature = sign_detached(noncanonical, PRIVATE_KEY, "test-key-1")
    result = verify_passport(noncanonical, signature, trust_bundle())
    assert result.schema_valid is True
    assert result.canonical_manifest is False
    assert result.errors == ["manifest_is_not_canonical"]


def test_expiry_and_retired_key_require_review_but_do_not_invalidate_history() -> None:
    payload, signature = signed_artifact()
    result = verify_passport(
        payload,
        signature,
        trust_bundle(status="retired"),
        at=datetime(2028, 1, 1, tzinfo=UTC),
    )
    assert result.signature_valid is True
    assert result.key_status == "retired"
    assert result.freshness == "expired"
    assert result.overall == "valid_review_required"


def test_revoked_key_is_invalid() -> None:
    payload, signature = signed_artifact()
    result = verify_passport(payload, signature, trust_bundle(status="revoked"))
    assert result.signature_valid is True
    assert result.key_status == "revoked"
    assert result.overall == "invalid"


def test_expected_scope_and_configuration_are_fail_closed() -> None:
    payload, signature = signed_artifact()
    result = verify_passport(
        payload,
        signature,
        trust_bundle(),
        expected_scope_fingerprint=content_digest("SCOPE", b"another workspace"),
    )
    assert result.scope_match == "invalid"
    assert result.overall == "invalid"
    assert result.errors == ["scope_fingerprint_mismatch"]


def test_missing_expiry_is_unknown_and_review_required() -> None:
    payload, signature = signed_artifact(manifest(not_after=None))
    result = verify_passport(payload, signature, trust_bundle())
    assert result.freshness == "unknown"
    assert result.overall == "valid_review_required"


def test_verification_time_before_issuance_is_invalid() -> None:
    payload, signature = signed_artifact()
    result = verify_passport(
        payload,
        signature,
        trust_bundle(),
        at=datetime(2026, 7, 31, tzinfo=UTC),
    )
    assert result.signature_valid is True
    assert result.errors == ["verification_time_precedes_issuance"]
