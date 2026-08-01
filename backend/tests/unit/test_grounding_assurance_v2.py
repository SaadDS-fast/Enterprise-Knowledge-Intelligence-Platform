import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_v2_blind_denominators_and_family_isolation():
    cases = json.loads((ROOT / "docs/evaluation/grounding-assurance-v2-cases.json").read_text())
    families = json.loads(
        (ROOT / "docs/evaluation/grounding-assurance-v2-families.json").read_text()
    )
    blind = [case for case in cases["cases"] if case["split"] == "blind"]
    counts = {
        decision: sum(case["expected_decision"] == decision for case in blind)
        for decision in ("ANSWER", "INSUFFICIENT_VERIFIED_SUPPORT", "CONFLICT")
    }
    assert counts == {"ANSWER": 360, "INSUFFICIENT_VERIFIED_SUPPORT": 405, "CONFLICT": 135}
    assert not (set(families["development_family_ids"]) & set(families["blind_family_ids"]))


def test_v2_preflight_and_single_execution_registration():
    preflight = json.loads(
        (ROOT / "docs/evaluation/grounding-assurance-v2-preflight.json").read_text()
    )
    freeze = json.loads((ROOT / "docs/evaluation/grounding-assurance-v2-freeze.json").read_text())
    assert preflight["status"] == "PASS"
    assert all(preflight["checks"].values())
    assert freeze["maximum_executions"] == 1
    assert freeze["executions_completed"] in {0, 1}
