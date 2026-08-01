"""Standalone command-line verifier for VAP-1 artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from app.passport.verifier import VerificationResult, verify_passport

VERIFIED_STATUSES = frozenset({"VERIFIED"})
REVIEW_REQUIRED_STATUSES = frozenset(
    {"VERIFIED_WITHOUT_SNAPSHOT", "STALE", "EXPIRED", "INDETERMINATE"}
)


def exit_classification(result: VerificationResult) -> tuple[int, str]:
    """Map verifier status to the stable automation contract."""

    if result.status in VERIFIED_STATUSES:
        return 0, "verified"
    if result.status in REVIEW_REQUIRED_STATUSES:
        return 2, "review_required"
    return 1, "invalid"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vap", description="Verify a VAP-1 passport offline")
    subparsers = parser.add_subparsers(dest="command", required=True)
    verify = subparsers.add_parser("verify", help="verify a detached VAP-1 artifact")
    verify.add_argument("manifest", type=Path)
    verify.add_argument("signature", type=Path)
    verify.add_argument("--trust-bundle", type=Path, required=True)
    verify.add_argument("--answer", type=Path)
    verify.add_argument("--snapshot", type=Path)
    verify.add_argument("--at", type=datetime.fromisoformat)
    verify.add_argument("--expected-scope-fingerprint")
    verify.add_argument("--expected-configuration-digest")
    verify.add_argument("--format", choices=("json", "text"), default="text")
    return parser


def _render_text(result: VerificationResult, exit_code: int, classification: str) -> str:
    lines = [
        f"status: {result.status}",
        f"overall: {result.overall}",
        f"exit_classification: {classification}",
        f"exit_code: {exit_code}",
        f"certificate_id: {result.certificate_id or '-'}",
        f"schema_valid: {str(result.schema_valid).lower()}",
        f"canonical_manifest: {str(result.canonical_manifest).lower()}",
        f"signature_valid: {str(result.signature_valid).lower()}",
        f"key_status: {result.key_status}",
        f"content_integrity: {result.content_integrity}",
        f"freshness: {result.freshness}",
    ]
    lines.extend(f"error: {error}" for error in result.errors)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = verify_passport(
            args.manifest.read_bytes(),
            args.signature.read_text(encoding="ascii").strip(),
            args.trust_bundle.read_bytes(),
            answer_bytes=args.answer.read_bytes() if args.answer else None,
            snapshot_bytes=args.snapshot.read_bytes() if args.snapshot else None,
            at=args.at,
            expected_scope_fingerprint=args.expected_scope_fingerprint,
            expected_configuration_digest=args.expected_configuration_digest,
        )
    except OSError as exc:
        result = VerificationResult(status="INVALID_SCHEMA", errors=[f"file_error:{exc}"])

    exit_code, classification = exit_classification(result)

    if args.format == "json":
        output = result.model_dump(mode="json") | {
            "exit_classification": classification,
            "exit_code": exit_code,
        }
        print(json.dumps(output, sort_keys=True, separators=(",", ":")))
    else:
        print(_render_text(result, exit_code, classification))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
