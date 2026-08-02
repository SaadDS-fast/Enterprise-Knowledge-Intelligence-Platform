from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.passport.cli import exit_classification, main
from app.passport.verifier import MAX_MANIFEST_BYTES, VerificationResult
from tests.unit.test_passport_core import ANSWER, signed_artifact, trust_bundle
from tests.unit.test_passport_validation_matrix import snapshot


def _write(path: Path, content: bytes) -> Path:
    path.write_bytes(content)
    return path


def test_cli_json_output_is_machine_readable_and_offline(tmp_path: Path, capsys) -> None:
    payload, signature = signed_artifact()
    manifest_path = _write(tmp_path / "passport.json", payload)
    signature_path = _write(tmp_path / "passport.sig", signature.encode("ascii"))
    trust_path = _write(tmp_path / "trust.json", trust_bundle())
    answer_path = _write(tmp_path / "answer.txt", ANSWER)
    snapshot_path = _write(tmp_path / "snapshot.json", snapshot())

    exit_code = main(
        [
            "verify",
            str(manifest_path),
            str(signature_path),
            "--trust-bundle",
            str(trust_path),
            "--answer",
            str(answer_path),
            "--snapshot",
            str(snapshot_path),
            "--at",
            "2026-08-01T00:00:00+00:00",
            "--format",
            "json",
        ]
    )

    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result["overall"] == "valid"
    assert result["status"] == "VERIFIED"
    assert result["exit_classification"] == "verified"
    assert result["exit_code"] == 0
    assert result["signature_valid"] is True


def test_cli_returns_nonzero_for_tampered_answer(tmp_path: Path, capsys) -> None:
    payload, signature = signed_artifact()
    manifest_path = _write(tmp_path / "passport.json", payload)
    signature_path = _write(tmp_path / "passport.sig", signature.encode("ascii"))
    trust_path = _write(tmp_path / "trust.json", trust_bundle())
    answer_path = _write(tmp_path / "answer.txt", b"tampered")

    exit_code = main(
        [
            "verify",
            str(manifest_path),
            str(signature_path),
            "--trust-bundle",
            str(trust_path),
            "--answer",
            str(answer_path),
            "--format",
            "json",
        ]
    )

    result = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert result["errors"] == ["answer_hash_mismatch"]


def test_cli_text_output_is_deterministic_and_contains_no_evidence(tmp_path: Path, capsys) -> None:
    payload, signature = signed_artifact()
    manifest_path = _write(tmp_path / "passport.json", payload)
    signature_path = _write(tmp_path / "passport.sig", signature.encode("ascii"))
    trust_path = _write(tmp_path / "trust.json", trust_bundle())
    arguments = [
        "verify",
        str(manifest_path),
        str(signature_path),
        "--trust-bundle",
        str(trust_path),
        "--at",
        "2026-08-01T00:00:00+00:00",
    ]
    assert main(arguments) == 2
    first = capsys.readouterr().out
    assert main(arguments) == 2
    second = capsys.readouterr().out
    assert first == second
    assert "Manager approval" not in first
    assert "PRIVATE" not in first


def test_cli_missing_malformed_and_oversized_files_are_normal_invalidity(
    tmp_path: Path, capsys
) -> None:
    missing = main(
        [
            "verify",
            str(tmp_path / "missing.json"),
            str(tmp_path / "missing.sig"),
            "--trust-bundle",
            str(tmp_path / "missing-trust.json"),
            "--format",
            "json",
        ]
    )
    assert missing == 1
    assert "Traceback" not in capsys.readouterr().out

    payload, signature = signed_artifact()
    manifest_path = _write(tmp_path / "passport.json", b"not-json")
    signature_path = _write(tmp_path / "passport.sig", signature.encode("ascii"))
    trust_path = _write(tmp_path / "trust.json", trust_bundle())
    assert (
        main(["verify", str(manifest_path), str(signature_path), "--trust-bundle", str(trust_path)])
        == 1
    )
    assert "Traceback" not in capsys.readouterr().out

    _write(manifest_path, b"x" * (MAX_MANIFEST_BYTES + 1))
    assert (
        main(["verify", str(manifest_path), str(signature_path), "--trust-bundle", str(trust_path)])
        == 1
    )
    assert "manifest_too_large" in capsys.readouterr().out
    assert payload


def test_cli_accepts_explicit_symlink_paths_without_path_interpretation(
    tmp_path: Path, capsys
) -> None:
    payload, signature = signed_artifact()
    real_manifest = _write(tmp_path / "real-passport.json", payload)
    manifest_link = tmp_path / "passport-link.json"
    manifest_link.symlink_to(real_manifest)
    signature_path = _write(tmp_path / "passport.sig", signature.encode("ascii"))
    trust_path = _write(tmp_path / "trust.json", trust_bundle())
    assert (
        main(
            [
                "verify",
                str(manifest_link),
                str(signature_path),
                "--trust-bundle",
                str(trust_path),
                "--at",
                "2026-08-01T00:00:00+00:00",
            ]
        )
        == 2
    )
    output = capsys.readouterr().out
    assert "status: VERIFIED_WITHOUT_SNAPSHOT" in output
    assert "exit_classification: review_required" in output
    assert "exit_code: 2" in output


def test_module_cli_form_runs(tmp_path: Path) -> None:
    payload, signature = signed_artifact()
    manifest_path = _write(tmp_path / "passport.json", payload)
    signature_path = _write(tmp_path / "passport.sig", signature.encode("ascii"))
    trust_path = _write(tmp_path / "trust.json", trust_bundle())
    completed = subprocess.run(  # noqa: S603 - fixed interpreter and module
        [
            sys.executable,
            "-m",
            "app.passport.cli",
            "verify",
            str(manifest_path),
            str(signature_path),
            "--trust-bundle",
            str(trust_path),
            "--at",
            "2026-08-01T00:00:00+00:00",
            "--format",
            "json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 2
    assert json.loads(completed.stdout)["status"] == "VERIFIED_WITHOUT_SNAPSHOT"


def test_installed_script_form_runs(tmp_path: Path) -> None:
    payload, signature = signed_artifact()
    manifest_path = _write(tmp_path / "passport.json", payload)
    signature_path = _write(tmp_path / "passport.sig", signature.encode("ascii"))
    trust_path = _write(tmp_path / "trust.json", trust_bundle())
    executable = Path(sys.executable).with_name("ekip-vap")
    assert executable.is_file()
    completed = subprocess.run(  # noqa: S603 - installed project entry point
        [
            str(executable),
            "verify",
            str(manifest_path),
            str(signature_path),
            "--trust-bundle",
            str(trust_path),
            "--at",
            "2026-08-01T00:00:00+00:00",
            "--format",
            "json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 2
    assert json.loads(completed.stdout)["status"] == "VERIFIED_WITHOUT_SNAPSHOT"


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("VERIFIED", (0, "verified")),
        ("VERIFIED_WITHOUT_SNAPSHOT", (2, "review_required")),
        ("STALE", (2, "review_required")),
        ("EXPIRED", (2, "review_required")),
        ("INDETERMINATE", (2, "review_required")),
        ("REVOKED", (1, "invalid")),
        ("INVALID_SIGNATURE", (1, "invalid")),
        ("CONTENT_MODIFIED", (1, "invalid")),
        ("SNAPSHOT_MISMATCH", (1, "invalid")),
        ("UNKNOWN_KEY", (1, "invalid")),
        ("INVALID_SCHEMA", (1, "invalid")),
        ("UNSUPPORTED_ALGORITHM", (1, "invalid")),
    ],
)
def test_cli_status_exit_contract(status: str, expected: tuple[int, str]) -> None:
    result = VerificationResult(status=status)  # type: ignore[arg-type]
    assert exit_classification(result) == expected
