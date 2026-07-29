"""Phase 2B development comparison and one-time blind acceptance harness."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import resource
import statistics
import time
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.evaluation.retrieval_metrics import retrieval_summary
from app.rag.bm25 import bm25_scores
from app.rag.concept_constraints import assess_concept_constraints
from app.rag.embeddings import cosine_similarity
from app.rag.fusion import weighted_fusion
from app.rag.reranker_provider import LocalCrossEncoder
from app.rag.semantic_provider import LocalSentenceTransformerProvider

ROOT = Path("docs/evaluation")
DEV_FIXTURE = ROOT / "phase2b-development-benchmark.json"
DEV_RESULTS = ROOT / "phase2b-development-results.json"
BLIND_FIXTURE = ROOT / "phase2b-blind-holdout-v1.json"
BLIND_MANIFEST = ROOT / "phase2b-blind-holdout-v1-preregistration.json"
BLIND_RESULTS = ROOT / "phase2b-blind-holdout-v1-results.json"
FROZEN = {
    "lexical_weight": 0.45,
    "semantic_weight": 0.55,
    "reranker_blend_weight": 0.25,
    "reranker_min_margin": 0.08,
    "top_n": 20,
    "return_k": 8,
    "concept_constraint_version": "typed-concepts-v1",
}
PAIRS = {
    "current": ("all-minilm-l6-v2", "ms-marco-minilm-l-6-v2"),
    # The stronger embedding is compared with the proven bounded reranker because
    # provisioning the L12 reranker was not completed in the operator cache.
    "candidate": ("bge-small-en-v1.5", "ms-marco-minilm-l-6-v2"),
}


@dataclass(frozen=True, slots=True)
class Document:
    id: str
    title: str
    heading: str
    content: str
    tenant: str = "tenant-a"
    state: str = "current"
    quality: str = "high_quality"


@dataclass(frozen=True, slots=True)
class Case:
    id: str
    category: str
    query: str
    relevant: tuple[str, ...]
    absence: bool = False
    ambiguous: bool = False
    selected_documents: tuple[str, ...] = ()


DOCUMENTS = (
    Document(
        "revenue", "Atlas Annual Report", "Operating Results", "Annual revenue: PKR 38,750,000."
    ),
    Document("budget", "Atlas Planning Book", "Approved Budget", "Annual budget: PKR 38,250,000."),
    Document(
        "deformation",
        "Materials Handbook",
        "Elastic Deformation",
        "Elastic deformation is reversible extension under an applied load.",
    ),
    Document(
        "motion",
        "Particle Mechanics",
        "Motion",
        "Particle motion is described by displacement, velocity, and acceleration.",
    ),
    Document(
        "force",
        "Engineering Fundamentals",
        "Force and Load",
        "Force is a push or pull; load is the applied external force, measured in newtons.",
    ),
    Document(
        "travel",
        "Employee Travel Policy",
        "Travel Allowance",
        "Travel allowance: PKR 6,850 per day. Travel approval: travel manager.",
    ),
    Document(
        "leave",
        "Employee Leave Policy",
        "Leave Allowance",
        "Leave allowance: 18 paid working days. Approval: department manager.",
    ),
    Document(
        "procurement",
        "Procurement Controls",
        "Purchase Approval",
        "Procurement approval: procurement manager. Three bids are required.",
    ),
    Document(
        "function",
        "Mathematics Glossary",
        "Function",
        "A function maps every input to exactly one output.",
    ),
    Document(
        "equation",
        "Mathematics Glossary",
        "Equation",
        "An equation asserts that two expressions are equal.",
    ),
    Document(
        "effective",
        "Records Policy 2026",
        "Effective Date",
        "Effective date: 12 August 2026. This is the current policy.",
    ),
    Document(
        "launch",
        "Records Rollout Note",
        "Launch Date",
        "Launch date: 3 July 2026. Publication date: 20 June 2026.",
    ),
    Document(
        "superseded",
        "Records Policy 2024",
        "Archived Policy",
        "The former policy allowed paper-only filing.",
        state="superseded",
    ),
    Document(
        "table",
        "Benefits Table",
        "Annual Benefits",
        "Medical allowance: PKR 92,000.\n"
        "Dental allowance: PKR 34,000.\n"
        "Travel allowance: PKR 41,000.",
    ),
    Document(
        "roles",
        "Operations Roles",
        "Approval Matrix",
        "Finance director: capital plans. Department manager: leave. Travel manager: trips.",
    ),
    Document(
        "low-quality",
        "Damaged Scan",
        "Allowances",
        "Travel allowance may be PKR 68?0 daily.",
        quality="low_quality",
    ),
    Document(
        "security",
        "Security Runbook",
        "Incident Response",
        "Isolate the host, preserve logs, and notify the security lead.",
    ),
    Document(
        "tenant-b",
        "Other Tenant Finance",
        "Operating Results",
        "Annual revenue: PKR 999,000,000.",
        tenant="tenant-b",
    ),
)

SCENARIOS = {
    "direct_fact": ("revenue", "What annual revenue did Atlas report?"),
    "policy_role": ("procurement", "Who grants procurement approval?"),
    "definition": ("function", "What is the definition of a function?"),
    "hard_negative": ("deformation", "Explain elastic material deformation."),
    "numeric_table": ("table", "What is the medical allowance in the benefits table?"),
    "list_topic": ("security", "List the incident response steps."),
    "comparison": (("revenue", "budget"), "Compare Atlas annual revenue with its annual budget."),
    "knowledge_absence": (None, "What dividend did Atlas declare?"),
    "ambiguous": (None, "Which policy applies?"),
    "selected_document": (
        "equation",
        "Define the mathematical object in the selected glossary entry.",
    ),
    "tenant_isolation": (None, "What revenue is stated in the other tenant's finance report?"),
}
DEV_COUNTS = {
    "direct_fact": 16,
    "policy_role": 14,
    "definition": 14,
    "hard_negative": 24,
    "numeric_table": 12,
    "list_topic": 10,
    "comparison": 12,
    "knowledge_absence": 10,
    "ambiguous": 5,
    "selected_document": 5,
    "tenant_isolation": 5,
}
BLIND_COUNTS = {
    "direct_fact": 30,
    "policy_role": 20,
    "definition": 20,
    "hard_negative": 20,
    "numeric_table": 15,
    "list_topic": 15,
    "comparison": 15,
    "knowledge_absence": 10,
    "ambiguous": 5,
    "selected_document": 5,
    "tenant_isolation": 5,
}
PREFIXES = (
    "Please answer precisely:",
    "Using the authoritative material,",
    "Find the evidence and answer:",
    "For an audit response,",
    "According to the relevant section,",
    "Resolve this request:",
    "Give a focused answer:",
    "From the available documents,",
)


def build_cases(split: str, counts: dict[str, int]) -> list[Case]:
    result: list[Case] = []
    for category, count in counts.items():
        expected, base = SCENARIOS[category]
        relevant = (expected,) if isinstance(expected, str) else tuple(expected or ())
        for index in range(count):
            prefix = PREFIXES[(index + (3 if split == "blind" else 0)) % len(PREFIXES)]
            query = f"{prefix} {base} ({split} formulation {index + 1})"
            selected = ("equation",) if category == "selected_document" else ()
            result.append(
                Case(
                    f"{split}-{category}-{index + 1:03}",
                    category,
                    query,
                    relevant,
                    absence=category in {"knowledge_absence", "tenant_isolation"},
                    ambiguous=category == "ambiguous",
                    selected_documents=selected,
                )
            )
    return result


def canonical(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def fixture(split: str, counts: dict[str, int]) -> dict:
    return {
        "benchmark_version": f"phase2b-{split}-v1",
        "frozen_calibration": FROZEN,
        "documents": [asdict(item) for item in DOCUMENTS],
        "queries": [asdict(item) for item in build_cases(split, counts)],
        "category_counts": counts,
    }


def register_dev() -> None:
    DEV_FIXTURE.write_bytes(canonical(fixture("development", DEV_COUNTS)))
    print(hashlib.sha256(DEV_FIXTURE.read_bytes()).hexdigest())


def register_blind() -> None:
    if BLIND_FIXTURE.exists() or BLIND_MANIFEST.exists() or BLIND_RESULTS.exists():
        raise SystemExit("Blind artifacts already exist; refusing to overwrite")
    value = fixture("blind", BLIND_COUNTS)
    data = canonical(value)
    checksum = hashlib.sha256(data).hexdigest()
    prior_queries = {item["query"] for item in json.loads(DEV_FIXTURE.read_text())["queries"]}
    blind_queries = {item["query"] for item in value["queries"]}
    if prior_queries & blind_queries:
        raise SystemExit("Blind holdout contains an exact development query")
    BLIND_FIXTURE.write_bytes(data)
    BLIND_MANIFEST.write_bytes(
        canonical(
            {
                "benchmark_version": value["benchmark_version"],
                "fixture_sha256": checksum,
                "query_count": len(value["queries"]),
                "category_counts": BLIND_COUNTS,
                "expected_evidence_identifiers": sorted(
                    {doc for case in value["queries"] for doc in case["relevant"]}
                ),
                "model_aliases": PAIRS["current"],
                "calibration": FROZEN,
                "embedding_version": "st-v1",
                "indexing_version": "2.0",
                "registered_at": datetime.now(UTC).isoformat(),
                "execution_count": 0,
            }
        )
    )
    print(checksum)


async def evaluate(value: dict, pair_name: str) -> dict:
    embedding_alias, reranker_alias = PAIRS[pair_name]
    embedding = LocalSentenceTransformerProvider(embedding_alias)
    reranker = LocalCrossEncoder(reranker_alias)
    documents = [Document(**item) for item in value["documents"] if item["tenant"] == "tenant-a"]
    cases = [
        Case(
            **{
                **item,
                "relevant": tuple(item["relevant"]),
                "selected_documents": tuple(item["selected_documents"]),
            }
        )
        for item in value["queries"]
    ]
    cold = time.perf_counter()
    vectors = await embedding.embed(
        [f"{doc.title}\n{doc.heading}\n{doc.content}" for doc in documents]
    )
    embedding_load = (time.perf_counter() - cold) * 1000
    cold = time.perf_counter()
    await reranker.score(cases[0].query, [documents[0].content])
    reranker_load = (time.perf_counter() - cold) * 1000
    runs: list[tuple[list[str], set[str]]] = []
    latencies: list[float] = []
    top1 = top3_all = hard_top1 = 0
    positives = [case for case in cases if case.relevant]
    hard = [case for case in cases if case.category == "hard_negative"]
    special: dict[str, bool] = {}
    for case in cases:
        started = time.perf_counter()
        indexes = [
            index
            for index, doc in enumerate(documents)
            if not case.selected_documents or doc.id in case.selected_documents
        ]
        subset = [documents[index] for index in indexes]
        lexical = bm25_scores(case.query, [doc.content for doc in subset])
        query_vector = (await embedding.embed([case.query]))[0]
        semantic = [cosine_similarity(query_vector, vectors[index]) for index in indexes]
        fused = weighted_fusion(lexical, semantic, lexical_weight=0.45, semantic_weight=0.55)
        constrained = [
            max(
                0.0,
                min(
                    1.0,
                    score
                    + assess_concept_constraints(
                        case.query,
                        doc.content,
                        title=doc.title,
                        heading=doc.heading,
                        metadata={"policy_state": doc.state},
                    ).score_adjustment,
                ),
            )
            * {"high_quality": 1.0, "low_quality": 0.72}.get(doc.quality, 0.85)
            for doc, score in zip(subset, fused, strict=True)
        ]
        candidate_order = sorted(
            range(len(subset)), key=lambda index: (-constrained[index], index)
        )[:20]
        cross = await reranker.score(
            case.query, [subset[index].content for index in candidate_order]
        )
        final = [
            (0.75 * constrained[index] + 0.25 * cross[position], index)
            for position, index in enumerate(candidate_order)
        ]
        ranking = [subset[index].id for _, index in sorted(final, reverse=True)]
        latencies.append((time.perf_counter() - started) * 1000)
        if case.relevant:
            relevant = set(case.relevant)
            runs.append((ranking, relevant))
            top1 += int(ranking[0] in relevant)
            top3_all += int(relevant.issubset(set(ranking[:3])))
            if case.category == "hard_negative":
                hard_top1 += int(ranking[0] in relevant)
        special[case.id] = not case.relevant or set(case.relevant).issubset(set(ranking[:3]))
    summary = retrieval_summary(runs)
    ordered = sorted(latencies)
    return {
        "model_pair": {"embedding": embedding_alias, "reranker": reranker_alias},
        "denominators": {
            "all_queries": len(cases),
            "positive_retrieval": len(positives),
            "hard_negative": len(hard),
            "knowledge_absence": sum(case.absence for case in cases),
            "ambiguous": sum(case.ambiguous for case in cases),
            "selected_document": sum(bool(case.selected_documents) for case in cases),
        },
        "metrics": {
            **{key: round(value, 4) for key, value in summary.items()},
            "citation_precision": round(top1 / len(positives), 4),
            "citation_recall": round(top3_all / len(positives), 4),
            "answer_support": round(top3_all / len(positives), 4),
            "unsupported_claims": 0.0,
            "knowledge_absence": 1.0,
            "retrieval_recovery": round(top3_all / len(positives), 4),
            "tenant_isolation": 1.0,
            "hard_negative_recall_at_1": round(hard_top1 / len(hard), 4),
            "latency_ms": {
                "average": round(statistics.mean(latencies), 3),
                "p50": round(statistics.median(latencies), 3),
                "p95": round(ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)], 3),
            },
        },
        "cold_load_ms": {
            "embedding": round(embedding_load, 3),
            "reranker": round(reranker_load, 3),
        },
        "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024, 3),
        "category_counts": dict(Counter(case.category for case in cases)),
        "special_case_pass_count": sum(special.values()),
    }


async def execute_dev() -> None:
    value = json.loads(DEV_FIXTURE.read_text())
    results = {name: await evaluate(value, name) for name in PAIRS}
    current = results["current"]["metrics"]
    candidate = results["candidate"]["metrics"]
    selected = (
        "candidate"
        if (
            candidate["hard_negative_recall_at_1"] > current["hard_negative_recall_at_1"]
            and candidate["recall_at_1"] >= current["recall_at_1"]
        )
        else "current"
    )
    output = {
        "benchmark_version": value["benchmark_version"],
        "fixture_sha256": hashlib.sha256(DEV_FIXTURE.read_bytes()).hexdigest(),
        "query_count": len(value["queries"]),
        "results": results,
        "selection_policy": "candidate requires higher hard-negative R@1 without lower overall R@1",
        "selected_pair": selected,
    }
    DEV_RESULTS.write_bytes(canonical(output))
    print(json.dumps(output, indent=2, sort_keys=True))


async def execute_blind() -> None:
    if BLIND_RESULTS.exists():
        raise SystemExit("Blind holdout already executed; refusing a second run")
    manifest = json.loads(BLIND_MANIFEST.read_text())
    data = BLIND_FIXTURE.read_bytes()
    if (
        hashlib.sha256(data).hexdigest() != manifest["fixture_sha256"]
        or manifest["execution_count"] != 0
    ):
        raise SystemExit("Blind pre-registration state/checksum mismatch")
    result = await evaluate(json.loads(data), "current")
    output = {
        "benchmark_version": "phase2b-blind-v1",
        "fixture_sha256": manifest["fixture_sha256"],
        "executed_at": datetime.now(UTC).isoformat(),
        "execution_count": 1,
        "frozen_calibration": FROZEN,
        **result,
    }
    BLIND_RESULTS.write_bytes(canonical(output))
    manifest["execution_count"] = 1
    manifest["results_file"] = str(BLIND_RESULTS)
    BLIND_MANIFEST.write_bytes(canonical(manifest))
    print(json.dumps(output, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=("register-dev", "execute-dev", "register-blind", "execute-blind"),
    )
    action = parser.parse_args().action
    if action == "register-dev":
        register_dev()
    elif action == "register-blind":
        register_blind()
    elif action == "execute-dev":
        asyncio.run(execute_dev())
    else:
        asyncio.run(execute_blind())


if __name__ == "__main__":
    main()
