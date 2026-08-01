from __future__ import annotations

import base64
import json
import socket
from datetime import UTC, datetime

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.passport.canonical import CanonicalizationError, canonicalize, parse_json_strict
from app.passport.hashing import b64url_encode, content_digest
from app.passport.issuer import IssuanceRejected, build_synthetic_manifest
from app.passport.jws import JWSError, sign_detached, verify_detached
from app.passport.verifier import verify_passport
from tests.unit.test_passport_core import (
    PRIVATE_KEY,
    manifest,
    signed_artifact,
    trust_bundle,
)


def snapshot(**updates: object) -> bytes:
    data: dict[str, object] = {
        "schema_version": "vap-snapshot-1",
        "certificate_id": "urn:uuid:12345678-1234-5678-9234-567812345678",
        "scope_fingerprint": content_digest("SCOPE", b"tenant/workspace"),
        "documents": [
            {
                "document_id": "document-1",
                "document_version": "1",
                "document_sha256": content_digest("DOCUMENT", b"document bytes"),
                "content_base64url": b64url_encode(b"document bytes"),
            }
        ],
        "evidence": [
            {
                "evidence_id": "evidence-1",
                "document_id": "document-1",
                "document_version": "1",
                "evidence_span_sha256": content_digest(
                    "EVIDENCE_SPAN", b"Manager approval is required for travel."
                ),
                "content_base64url": b64url_encode(b"Manager approval is required for travel."),
            }
        ],
    }
    data.update(updates)
    return canonicalize(data)


def issuance_input(**updates: object) -> dict[str, object]:
    data = manifest()
    data.update({"decision": "supported", "support_gate_passed": True})
    data.update(updates)
    return data


def resign(data: dict[str, object], *, key_id: str = "test-key-1") -> tuple[bytes, str]:
    payload = canonicalize(data)
    return payload, sign_detached(payload, PRIVATE_KEY, key_id)


def independent_b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def independent_sign(payload: bytes, header: dict[str, object]) -> str:
    protected_json = json.dumps(
        header, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    protected = independent_b64url(protected_json)
    encoded_payload = independent_b64url(payload)
    signature = PRIVATE_KEY.sign(f"{protected}.{encoded_payload}".encode("ascii"))
    return f"{protected}..{independent_b64url(signature)}"


def independent_verify(payload: bytes, envelope: str) -> dict[str, object]:
    protected, detached, signature = envelope.split(".")
    assert detached == ""
    header = json.loads(base64.urlsafe_b64decode(protected + "=" * (-len(protected) % 4)))
    raw_signature = base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
    signing_input = f"{protected}.{independent_b64url(payload)}".encode("ascii")
    PRIVATE_KEY.public_key().verify(raw_signature, signing_input)
    return header


def test_standard_encoded_detached_jws_interoperates_in_both_directions() -> None:
    payload, production_envelope = signed_artifact()
    header = independent_verify(payload, production_envelope)
    assert header == {
        "alg": "EdDSA",
        "kid": "test-key-1",
        "typ": "application/vap+jws",
    }

    independent_envelope = independent_sign(payload, header)
    assert verify_detached(payload, independent_envelope, PRIVATE_KEY.public_key()) == "test-key-1"
    assert verify_passport(payload, independent_envelope, trust_bundle()).signature_valid is True


@pytest.mark.parametrize(
    "header",
    [
        {"alg": "none", "kid": "test-key-1", "typ": "application/vap+jws"},
        {"alg": "HS256", "kid": "test-key-1", "typ": "application/vap+jws"},
        {"alg": "EdDSA", "kid": "test-key-1", "typ": "changed"},
        {"alg": "EdDSA", "kid": "changed", "typ": "application/vap+jws"},
        {"alg": "EdDSA", "kid": "test-key-1", "typ": "application/vap+jws", "cty": "x"},
        {
            "alg": "EdDSA",
            "kid": "test-key-1",
            "typ": "application/vap+jws",
            "crit": ["x"],
            "x": True,
        },
        {
            "alg": "EdDSA",
            "kid": "test-key-1",
            "typ": "application/vap+jws",
            "b64": False,
            "crit": ["b64"],
        },
        {"alg": "EdDSA", "kid": "test-key-1", "typ": "application/vap+jws", "b64": True},
    ],
)
def test_protected_header_profile_rejects_all_extensions_and_changes(
    header: dict[str, object],
) -> None:
    payload = canonicalize(manifest())
    envelope = independent_sign(payload, header)
    result = verify_passport(payload, envelope, trust_bundle())
    expected = "UNSUPPORTED_ALGORITHM" if header["alg"] != "EdDSA" else "INVALID_SIGNATURE"
    assert result.status == expected


def test_protected_header_must_be_canonical_and_have_no_duplicate_fields() -> None:
    payload = canonicalize(manifest())
    spaced = b'{ "alg":"EdDSA", "kid":"test-key-1", "typ":"application/vap+jws" }'
    protected = independent_b64url(spaced)
    signature = PRIVATE_KEY.sign(f"{protected}.{independent_b64url(payload)}".encode("ascii"))
    result = verify_passport(
        payload, f"{protected}..{independent_b64url(signature)}", trust_bundle()
    )
    assert result.status == "INVALID_SIGNATURE"
    assert result.errors == ["protected_header_not_canonical"]

    duplicate = b'{"alg":"EdDSA","alg":"EdDSA","kid":"test-key-1","typ":"application/vap+jws"}'
    protected = independent_b64url(duplicate)
    signature = PRIVATE_KEY.sign(f"{protected}.{independent_b64url(payload)}".encode("ascii"))
    result = verify_passport(
        payload, f"{protected}..{independent_b64url(signature)}", trust_bundle()
    )
    assert result.status == "INVALID_SIGNATURE"


def test_padded_noncanonical_and_unprotected_envelopes_are_rejected() -> None:
    payload, envelope = signed_artifact()
    protected, _, signature = envelope.split(".")
    for changed in [
        f"{protected}=..{signature}",
        f"{protected}..{signature}=",
        f"{protected}.unprotected.{signature}",
        f"{protected}...{signature}",
    ]:
        assert verify_passport(payload, changed, trust_bundle()).status == "INVALID_SIGNATURE"


def test_empty_detached_payload_is_rejected_by_profile() -> None:
    with pytest.raises(JWSError, match="empty_detached_payload"):
        sign_detached(b"", PRIVATE_KEY, "test-key-1")
    with pytest.raises(JWSError, match="empty_detached_payload"):
        verify_detached(b"", "AA..AA", PRIVATE_KEY.public_key())


def test_canonicalization_reference_matrix() -> None:
    vectors = [
        ({"b": 1, "a": 2}, b'{"a":2,"b":1}'),
        ({"n": {"z": 0, "a": -2}}, b'{"n":{"a":-2,"z":0}}'),
        ({"a": [3, 2, 1]}, b'{"a":[3,2,1]}'),
        (
            {"é": "café", "a": 'line\nquote"slash\\'},
            '{"a":"line\\nquote\\"slash\\\\","é":"café"}'.encode(),
        ),
        ({"integer": 9_007_199_254_740_991}, b'{"integer":9007199254740991}'),
        ({"negative": -7}, b'{"negative":-7}'),
    ]
    for value, expected in vectors:
        assert canonicalize(value) == expected
        assert canonicalize(json.loads(expected)) == expected


@pytest.mark.parametrize("value", [1.25, 1e20, float("nan"), float("inf"), float("-inf")])
def test_restricted_numeric_profile_rejects_fraction_exponent_and_nonfinite(value: float) -> None:
    with pytest.raises(CanonicalizationError):
        canonicalize({"number": value})


def test_unicode_is_not_normalized_and_invalid_surrogates_are_rejected() -> None:
    assert canonicalize({"value": "é"}) != canonicalize({"value": "e\u0301"})
    with pytest.raises(CanonicalizationError):
        canonicalize({"value": "\ud800"})


def test_deep_input_and_duplicate_keys_are_rejected() -> None:
    value: object = "leaf"
    for _ in range(66):
        value = [value]
    with pytest.raises(CanonicalizationError, match="maximum_json_depth"):
        canonicalize(value)
    with pytest.raises(CanonicalizationError, match="duplicate_json_key"):
        parse_json_strict(b'{"a":1,"a":2}')


def test_all_stable_hash_domains_and_protocol_version_are_separated() -> None:
    domains = ["PASSPORT", "ANSWER", "CLAIM", "EVIDENCE_SPAN", "DOCUMENT", "SCOPE", "CONFIG"]
    digests = {content_digest(domain, b"same") for domain in domains}
    assert len(digests) == len(domains)
    assert content_digest("ANSWER", b"same") == content_digest("ANSWER", b"same")
    assert content_digest("ANSWER", b"same") != content_digest("ANSWER", b"changed")
    assert content_digest("ANSWER", b"same") != content_digest(
        "ANSWER", b"same", protocol_version="VAP2"
    )
    assert content_digest("CLAIM", b"a\0bc") != content_digest("CLAIM", b"ab\0c")
    assert content_digest("PASSPORT", canonicalize({"a": 1, "b": 2})) == content_digest(
        "PASSPORT", canonicalize({"b": 2, "a": 1})
    )


@pytest.mark.parametrize("decision", ["refused", "unsupported", "operational_error"])
def test_synthetic_issuance_rejects_non_supported_decisions(decision: str) -> None:
    with pytest.raises(IssuanceRejected):
        build_synthetic_manifest(issuance_input(decision=decision))


def test_synthetic_issuance_accepts_only_complete_same_scope_mappings() -> None:
    result = build_synthetic_manifest(issuance_input())
    assert result.schema_version == "vap-1"

    cases = []
    no_gate = issuance_input(support_gate_passed=False)
    cases.append(no_gate)
    missing_gate_metadata = issuance_input()
    missing_gate_metadata["assurance"]["support_gate_version"] = ""
    cases.append(missing_gate_metadata)
    no_claims = issuance_input(claims=[])
    cases.append(no_claims)
    duplicate_claims = issuance_input()
    duplicate_claims["claims"] = [duplicate_claims["claims"][0]] * 2
    cases.append(duplicate_claims)
    no_citations = issuance_input()
    no_citations["claims"][0]["citations"] = []
    cases.append(no_citations)
    duplicate_citation = issuance_input()
    duplicate_citation["claims"][0]["citations"] = [
        duplicate_citation["claims"][0]["citations"][0]
    ] * 2
    cases.append(duplicate_citation)
    cross_scope = issuance_input()
    cross_scope["claims"][0]["citations"][0]["scope_fingerprint"] = content_digest(
        "SCOPE", b"other"
    )
    cases.append(cross_scope)
    malformed_document = issuance_input()
    malformed_document["claims"][0]["citations"][0]["document_sha256"] = "bad"
    cases.append(malformed_document)
    missing_document = issuance_input()
    del missing_document["claims"][0]["citations"][0]["document_id"]
    cases.append(missing_document)
    missing_config = issuance_input()
    del missing_config["assurance"]["retrieval_configuration_sha256"]
    cases.append(missing_config)
    missing_scope = issuance_input()
    del missing_scope["scope"]
    cases.append(missing_scope)
    inconsistent_version = issuance_input()
    second_citation = json.loads(json.dumps(inconsistent_version["claims"][0]["citations"][0]))
    second_citation["evidence_id"] = "evidence-2"
    second_citation["document_version"] = "2"
    inconsistent_version["claims"][0]["citations"].append(second_citation)
    cases.append(inconsistent_version)

    for case in cases:
        with pytest.raises(IssuanceRejected):
            build_synthetic_manifest(case)


def test_valid_snapshot_and_absent_snapshot_are_distinct() -> None:
    payload, signature = signed_artifact()
    verified = verify_passport(payload, signature, trust_bundle(), snapshot_bytes=snapshot())
    assert verified.status == "VERIFIED"
    assert verified.snapshot_integrity == "valid"

    absent = verify_passport(payload, signature, trust_bundle())
    assert absent.status == "VERIFIED_WITHOUT_SNAPSHOT"
    assert absent.snapshot_integrity == "not_supplied"


@pytest.mark.parametrize(
    ("update", "error"),
    [
        (
            {"certificate_id": "urn:uuid:22345678-1234-5678-9234-567812345678"},
            "snapshot_certificate_mismatch",
        ),
        ({"scope_fingerprint": content_digest("SCOPE", b"other")}, "snapshot_scope_mismatch"),
        ({"evidence": []}, "snapshot_schema_error"),
    ],
)
def test_snapshot_substitution_and_incomplete_sets_fail(
    update: dict[str, object], error: str
) -> None:
    payload, signature = signed_artifact()
    result = verify_passport(payload, signature, trust_bundle(), snapshot_bytes=snapshot(**update))
    assert result.status == "SNAPSHOT_MISMATCH"
    assert result.errors == [error]


def test_snapshot_content_and_version_mutations_fail() -> None:
    payload, signature = signed_artifact()
    for section, field, value in [
        ("documents", "content_base64url", b64url_encode(b"changed")),
        ("documents", "document_version", "2"),
        ("evidence", "content_base64url", b64url_encode(b"changed")),
        ("evidence", "document_id", "other"),
    ]:
        data = json.loads(snapshot())
        data[section][0][field] = value
        result = verify_passport(
            payload, signature, trust_bundle(), snapshot_bytes=canonicalize(data)
        )
        expected = "STALE" if field == "document_version" else "SNAPSHOT_MISMATCH"
        assert result.status == expected


def test_duplicate_and_unreferenced_snapshot_evidence_fail() -> None:
    payload, signature = signed_artifact()
    duplicate_data = json.loads(snapshot())
    duplicate_data["evidence"].append(duplicate_data["evidence"][0])
    duplicate = verify_passport(
        payload, signature, trust_bundle(), snapshot_bytes=canonicalize(duplicate_data)
    )
    assert duplicate.status == "SNAPSHOT_MISMATCH"

    extra_data = json.loads(snapshot())
    extra = json.loads(json.dumps(extra_data["evidence"][0]))
    extra["evidence_id"] = "unreferenced"
    extra_data["evidence"].append(extra)
    unreferenced = verify_passport(
        payload, signature, trust_bundle(), snapshot_bytes=canonicalize(extra_data)
    )
    assert unreferenced.errors == ["snapshot_evidence_set_mismatch"]


def _set_path(data: dict[str, object], path: tuple[object, ...], value: object) -> None:
    target: object = data
    for component in path[:-1]:
        target = target[component]  # type: ignore[index]
    target[path[-1]] = value  # type: ignore[index]


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("answer", "sha256"), content_digest("ANSWER", b"changed")),
        (("claims", 0, "normalized_sha256"), content_digest("CLAIM", b"changed")),
        (("claims", 0, "citations", 0, "evidence_id"), "changed-evidence"),
        (
            ("claims", 0, "citations", 0, "evidence_span_sha256"),
            content_digest("EVIDENCE_SPAN", b"changed"),
        ),
        (("claims", 0, "citations", 0, "document_id"), "changed-document"),
        (("claims", 0, "citations", 0, "document_version"), "2"),
        (("claims", 0, "citations", 0, "document_sha256"), content_digest("DOCUMENT", b"changed")),
        (("claims", 0, "citations", 0, "scope_fingerprint"), content_digest("SCOPE", b"changed")),
        (("scope", "tenant_workspace_fingerprint"), content_digest("SCOPE", b"changed")),
        (("scope", "audience"), "changed-audience"),
        (("assurance", "retrieval_configuration_sha256"), content_digest("CONFIG", b"changed")),
        (("assurance", "generation_provider_alias"), "changed-provider"),
        (("assurance", "approved_model_digest"), content_digest("CONFIG", b"model")),
        (("issued_at",), "2026-08-02T00:00:00Z"),
        (("freshness", "not_after"), "2028-01-01T00:00:00Z"),
        (("certificate_id",), "urn:uuid:22345678-1234-5678-9234-567812345678"),
        (("signing", "key_id"), "changed-key"),
        (("signing", "algorithm"), "HS256"),
        (("schema_version",), "vap-2"),
    ],
)
def test_every_manifest_security_field_is_signature_bound(
    path: tuple[object, ...], value: object
) -> None:
    payload, signature = signed_artifact()
    data = json.loads(payload)
    _set_path(data, path, value)
    result = verify_passport(canonicalize(data), signature, trust_bundle())
    assert result.overall == "invalid"


def test_claim_order_is_signature_bound() -> None:
    data = manifest()
    second = json.loads(json.dumps(data["claims"][0]))
    second["claim_id"] = "claim-2"
    second["citations"][0]["evidence_id"] = "evidence-2"
    data["claims"].append(second)
    payload, signature = resign(data)
    data["claims"].reverse()
    result = verify_passport(canonicalize(data), signature, trust_bundle())
    assert result.status == "INVALID_SIGNATURE"


def test_unknown_wrong_and_substituted_trust_keys_fail() -> None:
    payload, signature = signed_artifact()
    unknown = verify_passport(payload, signature, trust_bundle(key_id="another-key"))
    assert unknown.status == "UNKNOWN_KEY"

    wrong_key = Ed25519PrivateKey.generate().public_key().public_bytes_raw()
    wrong = verify_passport(payload, signature, trust_bundle(public_key=wrong_key))
    assert wrong.status == "INVALID_SIGNATURE"


def test_key_validity_interval_is_historical_and_current() -> None:
    payload, signature = signed_artifact()
    expired_now = verify_passport(
        payload,
        signature,
        trust_bundle(not_after="2026-12-31T00:00:00Z"),
        at=datetime(2027, 1, 1, tzinfo=UTC),
    )
    assert expired_now.historical_key_validity == "valid"
    assert expired_now.key_status == "expired"
    assert expired_now.status == "EXPIRED"

    outside = verify_passport(
        payload,
        signature,
        trust_bundle(not_before="2026-09-01T00:00:00Z"),
        at=datetime(2026, 10, 1, tzinfo=UTC),
    )
    assert outside.historical_key_validity == "outside_interval"
    assert outside.status == "INVALID_SIGNATURE"


def test_malformed_duplicate_and_unsupported_trust_bundles_fail() -> None:
    payload, signature = signed_artifact()
    malformed = verify_passport(payload, signature, b'{"bad":true}')
    assert malformed.status == "INVALID_SCHEMA"
    unsupported = verify_passport(payload, signature, trust_bundle(schema_version="vap-trust-2"))
    assert unsupported.status == "INVALID_SCHEMA"
    bundle = json.loads(trust_bundle())
    bundle["keys"].append(bundle["keys"][0])
    duplicate = verify_passport(payload, signature, canonicalize(bundle))
    assert duplicate.status == "INVALID_SCHEMA"
    bundle = json.loads(trust_bundle())
    bundle["keys"][0]["public_key"] = "AA"
    malformed_key = verify_passport(payload, signature, canonicalize(bundle))
    assert malformed_key.status == "INVALID_SCHEMA"


def test_unsupported_algorithm_and_unsigned_envelopes_fail() -> None:
    payload, _ = signed_artifact()
    header = b64url_encode(
        canonicalize({"alg": "HS256", "kid": "test-key-1", "typ": "application/vap+jws"})
    )
    unsupported = verify_passport(payload, f"{header}..AA", trust_bundle())
    assert unsupported.status == "UNSUPPORTED_ALGORITHM"
    unsigned = verify_passport(payload, "", trust_bundle())
    assert unsigned.status == "INVALID_SIGNATURE"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda signature: signature[:-5],
        lambda signature: signature[:-1] + "!",
        lambda signature: "AA" + signature[2:],
        lambda signature: signature.split(".")[0] + ".payload." + signature.split(".")[2],
    ],
)
def test_detached_envelope_corruption_is_rejected(mutate) -> None:
    payload, signature = signed_artifact()
    result = verify_passport(payload, mutate(signature), trust_bundle())
    assert result.status == "INVALID_SIGNATURE"


def test_signature_and_trust_bundle_substitution_are_rejected() -> None:
    payload, _ = signed_artifact()
    other_key = Ed25519PrivateKey.generate()
    substituted_signature = sign_detached(payload, other_key, "test-key-1")
    result = verify_passport(payload, substituted_signature, trust_bundle())
    assert result.status == "INVALID_SIGNATURE"

    payload, signature = signed_artifact()
    substituted_bundle = trust_bundle(public_key=other_key.public_key().public_bytes_raw())
    result = verify_passport(payload, signature, substituted_bundle)
    assert result.status == "INVALID_SIGNATURE"


def test_verification_never_creates_network_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*args: object, **kwargs: object) -> None:
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)
    payload, signature = signed_artifact()
    result = verify_passport(payload, signature, trust_bundle(), snapshot_bytes=snapshot())
    assert result.status == "VERIFIED"


def test_compound_failure_precedence_preserves_integrity_and_trust_failures() -> None:
    payload, signature = signed_artifact()
    expired_at = datetime(2028, 1, 1, tzinfo=UTC)

    modified_and_expired = verify_passport(
        payload,
        signature,
        trust_bundle(),
        answer_bytes=b"modified",
        at=expired_at,
    )
    assert modified_and_expired.status == "CONTENT_MODIFIED"

    unknown_and_bad_snapshot = verify_passport(
        payload,
        signature,
        trust_bundle(key_id="unknown"),
        snapshot_bytes=b"bad",
    )
    assert unknown_and_bad_snapshot.status == "UNKNOWN_KEY"

    stale_data = json.loads(snapshot())
    stale_data["documents"][0]["document_version"] = "2"
    stale_snapshot = canonicalize(stale_data)
    corrupted = signature[:-1] + ("A" if signature[-1] != "A" else "B")
    invalid_and_stale = verify_passport(
        payload, corrupted, trust_bundle(), snapshot_bytes=stale_snapshot
    )
    assert invalid_and_stale.status == "INVALID_SIGNATURE"

    mismatch_and_expired = verify_passport(
        payload,
        signature,
        trust_bundle(),
        snapshot_bytes=canonicalize(
            json.loads(snapshot()) | {"scope_fingerprint": content_digest("SCOPE", b"different")}
        ),
        at=expired_at,
    )
    assert mismatch_and_expired.status == "SNAPSHOT_MISMATCH"
