import importlib.util
from collections import Counter
from pathlib import Path


def _module():
    path = Path(__file__).resolve().parents[3] / "scripts" / "enterprise_corpus.py"
    spec = importlib.util.spec_from_file_location("enterprise_corpus", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_enterprise_corpus_is_balanced_synthetic_and_checksummed():
    module = _module()
    records = module.corpus()

    assert len(records) == 100
    assert set(Counter(item["department"] for item in records).values()) == {10}
    assert set(Counter(item["file_type"] for item in records).values()) == {10}
    assert all(len(item["sha256"]) == 64 for item in records)
    assert all(item["tenant"] in {"Tenant A", "Tenant B", "Tenant C"} for item in records)


def test_enterprise_acceptance_matrix_has_complete_contract_fields():
    module = _module()
    cases = module.acceptance_matrix()
    required = {
        "case_id",
        "preconditions",
        "tenant",
        "workspace",
        "role",
        "documents",
        "feature_flags",
        "action",
        "expected_http_status",
        "expected_canonical_state",
        "expected_claims",
        "expected_citations",
        "expected_fallback_category",
        "expected_security_result",
    }

    assert len(cases) == 118
    assert len({case["case_id"] for case in cases}) == len(cases)
    assert all(required <= case.keys() for case in cases)


def test_runtime_binary_fixtures_are_reproducible_and_structured():
    module = _module()
    text = module._content(2, "Human Resources")

    assert module.render("docx", text) == module.render("docx", text)
    html = module.render("html", text).decode()
    assert "<main>" in html and "<p>" in html
    assert "<pre>" not in html
