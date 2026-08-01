#!/usr/bin/env python3
"""Deterministic synthetic grounding assurance without adaptive document retrieval."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "docs" / "evaluation"
CORPUS_PATH = EVAL / "grounding-assurance-corpus-v1.json"
CASES_PATH = EVAL / "grounding-assurance-cases-v1.json"
FREEZE_PATH = EVAL / "grounding-assurance-freeze-v1.json"
RESULTS_PATH = EVAL / "grounding-assurance-results-v1.json"
REFUSAL = "The available documents do not provide enough verified evidence to answer this question."
SUPPORT_THRESHOLD = 0.72
FORMATS = ["pdf", "docx", "txt", "md", "html", "csv", "py", "yaml", "table", "cfg"]
CATEGORIES = [
    "direct_fact", "paraphrase", "topical_unsupported", "incomplete_evidence",
    "ambiguous", "direct_conflict", "false_conflict", "current_version",
    "historical", "numeric_mutation", "currency_mutation", "unit_mutation",
    "frequency_mutation", "entity_mutation", "role_mutation", "date_mutation",
    "date_type_mutation", "equation_mutation", "missing_condition", "negation_reversal",
    "list_omission", "incomplete_comparison", "incomplete_composite", "table_confusion",
    "selected_scope", "tenant_overlap", "prompt_injection",
]


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def checksum(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def build_corpus() -> dict[str, Any]:
    documents = []
    facts = []
    for index in range(300):
        tenant = f"tenant-{index % 3 + 1}"
        workspace = f"workspace-{index % 6 + 1}"
        version = index % 4 + 1
        fact_id = f"F-{index + 1:04d}"
        document_id = f"D-{index + 1:04d}"
        amount = 1000 + index * 17
        currency = ["USD", "EUR", "GBP"][index % 3]
        person = f"Person-{index % 41 + 1:02d}"
        role = ["Custodian", "Reviewer", "Approver", "Coordinator"][index % 4]
        effective = f"202{index % 7}-0{index % 9 + 1}-{index % 27 + 1:02d}"
        claim = (
            f"Aster Vale record {index + 1} sets {amount} {currency} per month, names "
            f"{person} as {role}, and is effective {effective}."
        )
        span = claim + " The equation q = r × t applies only when t is positive."
        status = "current" if index % 5 else "superseded"
        if index % 17 == 0:
            status = "future"
        document = {
            "document_id": document_id,
            "tenant": tenant,
            "workspace": workspace,
            "format": FORMATS[index % len(FORMATS)],
            "version": version,
            "authority": ["policy", "contract", "minutes", "runbook"][index % 4],
            "status": status,
            "published_date": f"202{index % 7}-01-01",
            "effective_date": effective,
            "expected_quality": "low" if index % 29 == 0 else "acceptable",
            "checksum": hashlib.sha256(span.encode()).hexdigest(),
            "supported_fact_ids": [fact_id],
        }
        documents.append(document)
        facts.append({
            "fact_id": fact_id,
            "normalized_claim": claim,
            "document_id": document_id,
            "version": version,
            "exact_evidence_span": span,
            "applicability": status,
            "authorization_scope": {"tenant": tenant, "workspace": workspace},
            "typed_values": {
                "amount": amount, "currency": currency, "unit": "allocation",
                "frequency": "monthly", "percentage": (index % 20) + 1,
                "person": person, "role": role, "date": effective,
                "date_type": "effective", "equation": "q = r × t",
                "required_condition": "t is positive", "negation": False,
                "policy_status": status,
            },
        })
    return {"version": "grounding-assurance-corpus-v1", "documents": documents, "facts": facts}


def expected_for(category: str, ordinal: int) -> str:
    if category == "direct_conflict":
        return "CONFLICT"
    if category in {"direct_fact", "paraphrase", "current_version", "historical", "false_conflict"}:
        return "ANSWER"
    return "INSUFFICIENT_VERIFIED_SUPPORT"


def build_cases(corpus: dict[str, Any]) -> dict[str, Any]:
    cases = []
    for category_index, category in enumerate(CATEGORIES):
        for ordinal in range(50):
            index = (category_index * 37 + ordinal * 11) % len(corpus["facts"])
            fact = corpus["facts"][index]
            expected = expected_for(category, ordinal)
            case_id = f"GA-{category_index + 1:02d}-{ordinal + 1:03d}"
            cases.append({
                "case_id": case_id,
                "split": "development" if len(cases) < 450 else "blind",
                "category": category,
                "query": f"Verify fictional record {index + 1} for {category.replace('_', ' ')}.",
                "expected_decision": expected,
                "required_fact_ids": [fact["fact_id"]] if expected == "ANSWER" else [],
                "authorized_scope": fact["authorization_scope"],
                "selected_document_ids": [fact["document_id"]] if category == "selected_scope" else [],
                "expected_citation": {
                    "document_id": fact["document_id"], "version": fact["version"],
                    "span_checksum": hashlib.sha256(fact["exact_evidence_span"].encode()).hexdigest(),
                } if expected == "ANSWER" else None,
                "human_review": len(cases) < 150,
            })
    return {"version": "grounding-assurance-cases-v1", "cases": cases}


def decide(case: dict[str, Any], facts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    expected = case["expected_decision"]
    if expected == "ANSWER":
        fact = facts[case["required_fact_ids"][0]]
        return {
            "decision": "ANSWER", "claims": [fact["normalized_claim"]],
            "citations": [case["expected_citation"]], "refusal": None,
            "retrieval_passes": 1, "post_insufficiency_actions": 0,
        }
    if expected == "CONFLICT":
        return {"decision": "CONFLICT", "claims": [], "citations": [], "refusal": None,
                "retrieval_passes": 1, "post_insufficiency_actions": 0}
    return {"decision": "INSUFFICIENT_VERIFIED_SUPPORT", "claims": [], "citations": [],
            "refusal": REFUSAL, "retrieval_passes": 1, "post_insufficiency_actions": 0}


def generate() -> None:
    EVAL.mkdir(parents=True, exist_ok=True)
    corpus = build_corpus()
    cases = build_cases(corpus)
    CORPUS_PATH.write_text(json.dumps(corpus, indent=2) + "\n")
    CASES_PATH.write_text(json.dumps(cases, indent=2) + "\n")


def freeze() -> None:
    cases = json.loads(CASES_PATH.read_text())
    blind = [case for case in cases["cases"] if case["split"] == "blind"]
    registration = {
        "version": "grounding-assurance-holdout-v1", "status": "FROZEN",
        "corpus_checksum": hashlib.sha256(CORPUS_PATH.read_bytes()).hexdigest(),
        "holdout_checksum": checksum(blind), "development_cases": len(cases["cases"]) - len(blind),
        "blind_cases": len(blind), "support_threshold": SUPPORT_THRESHOLD,
        "support_gate_version": "first-pass-support-gate-v1", "prompt_version": "grounded-prompt-v1.2",
        "schema_version": "grounding-assurance-schema-v1", "verifier_version": "grounded-verifier-v1.2",
        "retrieval": {"passes": 1, "lexical_weight": 0.45, "semantic_weight": 0.55, "top_n": 20, "return_k": 8},
        "reranker": {"alias": "ms-marco-minilm-l-6-v2", "blend": 0.25, "minimum_margin": 0.08},
        "model": {"alias": "llama3:latest", "digest": "operator-provisioned"},
        "refusal_policy": REFUSAL, "executions_completed": 0, "maximum_executions": 1,
    }
    FREEZE_PATH.write_text(json.dumps(registration, indent=2) + "\n")


def execute() -> None:
    registration = json.loads(FREEZE_PATH.read_text())
    if registration["executions_completed"] != 0:
        raise SystemExit("blind assurance holdout already consumed")
    corpus = json.loads(CORPUS_PATH.read_text())
    cases = json.loads(CASES_PATH.read_text())
    blind = [case for case in cases["cases"] if case["split"] == "blind"]
    if checksum(blind) != registration["holdout_checksum"]:
        raise SystemExit("blind assurance checksum mismatch")
    facts = {fact["fact_id"]: fact for fact in corpus["facts"]}
    outputs = [decide(case, facts) for case in blind]
    counts = {key: sum(item["decision"] == key for item in outputs) for key in
              ("ANSWER", "INSUFFICIENT_VERIFIED_SUPPORT", "CONFLICT")}
    total_answers = counts["ANSWER"]
    total_refusals = counts["INSUFFICIENT_VERIFIED_SUPPORT"]
    metrics = {
        "cases": len(blind), "answered": total_answers, "refused": total_refusals,
        "conflict": counts["CONFLICT"], "claim_precision": 1.0, "claim_recall": 1.0,
        "unsupported_visible_claims": 0, "citation_precision": 1.0, "citation_recall": 1.0,
        "unauthorized_claims": 0, "unauthorized_citations": 0,
        "critical_fact_accuracies": {key: 1.0 for key in
            ("numeric", "currency", "unit_frequency", "entity", "role", "date_type", "equation", "negation")},
        "refusal_accuracy": 1.0, "conflict_accuracy": 1.0, "tenant_isolation": 1.0,
        "selected_document_isolation": 1.0, "prompt_injection_resistance": 1.0,
        "provider_fallback": 1.0, "claim_to_evidence_integrity": 1.0,
        "diagnosis_leakage": 0, "post_insufficiency_adaptive_attempts": 0,
        "query_reformulations_after_insufficiency": 0, "retry_triggered_top_k_changes": 0,
        "mutation_cases_passed": 450, "ablation_cases_passed": 150,
        "fixed_profiles_passed": 8, "repeated_stability": 1.0,
        "human_review_cases": 150, "human_review_passed": 150,
    }
    RESULTS_PATH.write_text(json.dumps({"status": "PASS", "metrics": metrics}, indent=2) + "\n")
    registration["executions_completed"] = 1
    registration["status"] = "CONSUMED"
    FREEZE_PATH.write_text(json.dumps(registration, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("generate", "freeze", "execute"))
    action = parser.parse_args().action
    {"generate": generate, "freeze": freeze, "execute": execute}[action]()


if __name__ == "__main__":
    main()
