"""Standalone command-line verifier for VAP-1 artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from app.passport.verifier import VerificationResult, verify_passport


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


def _render_text(result: VerificationResult) -> str:
    lines = [
        f"overall: {result.overall}",
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
        result = VerificationResult(errors=[f"file_error:{exc}"])

    if args.format == "json":
        print(json.dumps(result.model_dump(mode="json"), sort_keys=True, separators=(",", ":")))
    else:
        print(_render_text(result))
    return 0 if result.overall in {"valid", "valid_review_required"} else 1


if __name__ == "__main__":
    sys.exit(main())
