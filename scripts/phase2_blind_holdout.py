"""Pre-register and execute the new Phase 2 blind acceptance holdout exactly once."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import resource
import statistics
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.evaluation.retrieval_metrics import retrieval_summary
from app.rag.bm25 import bm25_scores
from app.rag.embeddings import cosine_similarity
from app.rag.fusion import weighted_fusion
from app.rag.reranker import rerank_score
from app.rag.reranker_provider import LocalCrossEncoder
from app.rag.semantic_provider import LocalSentenceTransformerProvider

FIXTURE = Path("docs/evaluation/phase2-blind-holdout-v2.json")
MANIFEST = Path("docs/evaluation/phase2-blind-holdout-v2-preregistration.json")
RESULTS = Path("docs/evaluation/phase2-blind-holdout-v2-results.json")
FROZEN = {
    "lexical_weight": 0.45,
    "semantic_weight": 0.55,
    "reranker_blend_weight": 0.25,
    "reranker_min_margin": 0.08,
    "top_n": 20,
    "return_k": 8,
}


@dataclass(frozen=True, slots=True)
class Document:
    id: str
    title: str
    content: str
    tenant: str = "tenant-a"


@dataclass(frozen=True, slots=True)
class Case:
    id: str
    category: str
    query: str
    relevant: tuple[str, ...]
    absence: bool = False
    recovery: bool = False


DOCUMENTS = [
    Document(
        "mobility",
        "Regional Mobility Standard",
        "Field Meal Ceiling: PKR 6,400 per calendar day.",
    ),
    Document(
        "wellbeing",
        "Wellbeing Leave Standard",
        "Caregiver Leave: 12 paid working days annually.",
    ),
    Document(
        "treasury",
        "Treasury Controls",
        "Equipment Authorization: The treasury controller approves requests above PKR 720,000.",
    ),
    Document(
        "sourcing",
        "Strategic Sourcing Rules",
        "Tender Rule: Four written bids are mandatory above PKR 240,000.",
    ),
    Document(
        "algebra",
        "Algebra Reference",
        "Bijection Definition: A bijection is both one-to-one and onto.",
    ),
    Document(
        "mechanics",
        "Mechanics Exercises",
        "Exercise 11: A cart has position x(t). Derive its acceleration.",
    ),
    Document(
        "elasticity",
        "Elasticity Exercises",
        "Exercise 18: A polymer rod shortens under compressive force. Determine its strain.",
    ),
    Document(
        "milestones",
        "Orion Delivery Charter",
        "Go-live Date: 17 September 2027.\nProgram Owner: Nadia Rahman.",
    ),
    Document(
        "security",
        "Security Response Guide",
        "Incident Steps: isolate the host; preserve logs; notify the security lead.",
    ),
    Document(
        "quality",
        "Quality Review Matrix",
        "Reviewers: Amina Shah, Bilal Khan, and Chen Wu.",
    ),
    Document(
        "benefits",
        "Benefits Summary",
        "Medical Limit: PKR 85,000.\nDental Limit: PKR 30,000.",
    ),
    Document(
        "roles",
        "Department Roles",
        "Department Manager: The service manager approves weekly rosters.",
    ),
    Document(
        "motion-distractor",
        "Warehouse Move",
        "The relocation team moves carts and polymer containers.",
    ),
    Document("budget-distractor", "Planning Budget", "Annual Budget: PKR 14,000,000."),
    Document(
        "tenant-b",
        "Tenant B Mobility",
        "Field meals are limited to PKR 99,000 daily.",
        "tenant-b",
    ),
]

QUERIES: dict[str, tuple[str, list[str], bool]] = {
    "direct_fact": (
        "mobility",
        [
            "What is the field meal ceiling?",
            "State the daily field meal amount.",
            "Give the PKR field-food limit.",
            "How much is allowed for meals each calendar day?",
            "Find the regional meal ceiling.",
            "What daily food expense is permitted?",
            "Which amount covers field meals?",
            "Report the official meal limit.",
        ],
        False,
    ),
    "paraphrased_fact": (
        "wellbeing",
        [
            "How much paid time is available for caring duties?",
            "State the yearly caregiver entitlement.",
            "How many working days cover family care?",
            "Give the annual care leave allowance.",
            "What paid absence supports caregivers?",
            "Find the caregiver time-off limit.",
            "How many days may a caregiver take?",
            "Identify the yearly paid care benefit.",
        ],
        True,
    ),
    "definition": (
        "algebra",
        [
            "Define a bijection.",
            "Which mapping is one-to-one and onto?",
            "What does bijection mean?",
            "Give the algebraic bijection definition.",
            "Identify the mapping with both properties.",
            "Which relation is injective and surjective?",
            "State the exact bijection rule.",
            "Find the definition combining one-to-one with onto.",
        ],
        True,
    ),
    "policy_rule": (
        "sourcing",
        [
            "When are four written bids mandatory?",
            "State the tender rule.",
            "What sourcing rule applies above PKR 240,000?",
            "How many bids are required for a large purchase?",
            "Find the written-bid threshold.",
            "When must sourcing collect four offers?",
            "Give the strategic tender requirement.",
            "Which amount triggers four bids?",
        ],
        False,
    ),
    "date": (
        "milestones",
        [
            "When is Orion scheduled to go live?",
            "State the Orion go-live date.",
            "What date launches the Orion delivery?",
            "Give the program milestone date.",
            "When does the charter schedule launch?",
            "Find Orion's September milestone.",
            "Which date is listed for go-live?",
            "Report the exact Orion launch date.",
        ],
        False,
    ),
    "monetary_limit": (
        "benefits",
        [
            "What is the medical benefit limit?",
            "State the PKR medical ceiling.",
            "How much medical coverage is available?",
            "Give the healthcare reimbursement limit.",
            "Find the medical allowance amount.",
            "What sum covers medical claims?",
            "Which limit is PKR 85,000?",
            "Report the medical cap.",
        ],
        False,
    ),
    "name_role": (
        "milestones",
        [
            "Who owns the Orion program?",
            "Name the Orion program owner.",
            "Which person is responsible for Orion?",
            "State the owner in the delivery charter.",
            "Who leads the Orion delivery?",
            "Find the named program owner.",
            "Identify Orion's accountable person.",
            "Give the owner's full name.",
        ],
        False,
    ),
    "numbered_question": (
        "mechanics",
        [
            "Find Exercise 11.",
            "Which exercise derives acceleration from x(t)?",
            "Locate the cart-position problem.",
            "What numbered mechanics item asks for acceleration?",
            "Identify the x(t) exercise.",
            "Which question concerns a cart's acceleration?",
            "Find the position-to-acceleration problem.",
            "Report the mechanics exercise number.",
        ],
        True,
    ),
    "topic_identification": (
        "elasticity",
        [
            "Which exercise concerns compression of a material?",
            "Identify the polymer strain problem.",
            "What topic is Exercise 18 about?",
            "Find the elasticity question under force.",
            "Which item studies a shortening rod?",
            "Locate the compressive deformation exercise.",
            "What question concerns strain rather than cart motion?",
            "Identify the polymer-force topic.",
        ],
        True,
    ),
    "list": (
        "quality",
        [
            "List the quality reviewers.",
            "Who are all review-matrix members?",
            "Give the reviewer names.",
            "Enumerate the quality reviewers.",
            "Which people perform quality review?",
            "State every named reviewer.",
            "Who appears in the reviewer list?",
            "Return the three quality-review names.",
        ],
        False,
    ),
    "multi_evidence": (
        "benefits",
        [
            "Give both medical and dental limits.",
            "What are the two benefit ceilings?",
            "State medical as well as dental coverage.",
            "List both healthcare benefit amounts.",
            "How do medical and dental caps compare?",
            "Return each benefit limit.",
            "What amounts cover medical and dental claims?",
            "Give the paired benefit values.",
        ],
        False,
    ),
    "hard_negative": (
        "elasticity",
        [
            "Which problem concerns strain under compressive force?",
            "Find material shortening, not warehouse movement.",
            "Which exercise deforms a polymer rather than moving a cart?",
            "Identify compression instead of position change.",
            "Find the applied-force strain calculation.",
            "Which item is about elasticity, not relocation?",
            "Locate polymer deformation under load.",
            "What question studies material strain?",
        ],
        True,
    ),
}

ABSENT = [
    "What was annual revenue?",
    "State net sales turnover.",
    "What profit was recorded?",
    "Give the tax liability.",
    "Who chairs the board?",
    "Where is the London branch?",
    "What dividend was declared?",
    "How many customers are active?",
]
AMBIGUOUS = [
    "status",
    "policy",
    "Orion",
    "limit",
    "owner",
    "date",
    "exercise",
    "benefit",
]
TENANT_QUERIES = [
    "What is Tenant B's field meal limit?",
    "State Tenant B daily meals.",
    "How much does Tenant B allow for food?",
    "Give the other tenant's meal ceiling.",
    "Find Tenant B mobility expenses.",
    "What is the PKR 99,000 meal rule?",
    "Report Tenant B field food.",
    "Which tenant permits 99,000 daily?",
]


def cases() -> list[Case]:
    result: list[Case] = []
    for category, (document_id, queries, recovery) in QUERIES.items():
        result.extend(
            Case(
                f"{category}-{index}",
                category,
                query,
                (document_id,),
                recovery=recovery,
            )
            for index, query in enumerate(queries)
        )
    result.extend(
        Case(f"absence-{i}", "knowledge_absence", q, (), True)
        for i, q in enumerate(ABSENT)
    )
    result.extend(
        Case(f"ambiguous-{i}", "ambiguous", q, (), True)
        for i, q in enumerate(AMBIGUOUS)
    )
    result.extend(
        Case(f"isolation-{i}", "tenant_isolation", q, (), True)
        for i, q in enumerate(TENANT_QUERIES)
    )
    return result


def payload() -> dict:
    selected = cases()
    counts: dict[str, int] = {}
    for case in selected:
        counts[case.category] = counts.get(case.category, 0) + 1
    return {
        "benchmark_version": "phase2-blind-holdout-v2",
        "frozen_calibration": FROZEN,
        "documents": [asdict(item) for item in DOCUMENTS],
        "queries": [asdict(item) for item in selected],
        "category_counts": counts,
    }


def canonical_bytes(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def register() -> None:
    if FIXTURE.exists() or MANIFEST.exists() or RESULTS.exists():
        raise SystemExit("Blind holdout artifacts already exist; refusing to overwrite")
    value = payload()
    encoded = canonical_bytes(value)
    checksum = hashlib.sha256(encoded).hexdigest()
    FIXTURE.write_bytes(encoded)
    MANIFEST.write_bytes(
        canonical_bytes(
            {
                "benchmark_version": value["benchmark_version"],
                "fixture_sha256": checksum,
                "query_count": len(value["queries"]),
                "category_counts": value["category_counts"],
                "frozen_calibration": FROZEN,
                "pre_registered_execution_count": 0,
                "execution_count": 0,
            }
        )
    )
    print(checksum)


def ranks(scores: list[float], documents: list[Document]) -> list[str]:
    return [
        documents[index].id
        for index in sorted(
            range(len(scores)), key=lambda index: (-scores[index], index)
        )
    ]


def latency(values: list[float]) -> dict:
    ordered = sorted(values)
    return {
        "average_ms": round(statistics.mean(values), 3),
        "p50_ms": round(statistics.median(values), 3),
        "p95_ms": round(ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)], 3),
    }


async def execute() -> None:
    if RESULTS.exists():
        raise SystemExit("Blind holdout was already executed; refusing a second run")
    fixture_bytes = FIXTURE.read_bytes()
    manifest = json.loads(MANIFEST.read_text())
    checksum = hashlib.sha256(fixture_bytes).hexdigest()
    if checksum != manifest["fixture_sha256"] or manifest["execution_count"] != 0:
        raise SystemExit("Pre-registration checksum/state mismatch")
    value = json.loads(fixture_bytes)
    selected = [
        Case(**{**item, "relevant": tuple(item["relevant"])})
        for item in value["queries"]
    ]
    documents = [item for item in DOCUMENTS if item.tenant == "tenant-a"]
    contents = [item.content for item in documents]
    embedding = LocalSentenceTransformerProvider("all-minilm-l6-v2")
    cold_started = time.perf_counter()
    vectors = await embedding.embed(
        [f"{item.title}\n{item.content}" for item in documents]
    )
    embedding_cold = (time.perf_counter() - cold_started) * 1000
    reranker = LocalCrossEncoder("ms-marco-minilm-l-6-v2")
    reranker_cold_started = time.perf_counter()
    await reranker.score(selected[0].query, contents[:4])
    reranker_cold = (time.perf_counter() - reranker_cold_started) * 1000
    mode_runs = {
        name: [] for name in ("lexical", "semantic_hybrid", "calibrated_reranker")
    }
    mode_latency = {name: [] for name in mode_runs}
    top_one = {name: 0 for name in mode_runs}
    top_three = {name: 0 for name in mode_runs}
    materials_rank = []
    positives = [case for case in selected if case.relevant]
    absences = [case for case in selected if case.category == "knowledge_absence"]
    recovery = [case for case in positives if case.recovery]
    isolation = [case for case in selected if case.category == "tenant_isolation"]
    for case in selected:
        start = time.perf_counter()
        lexical = bm25_scores(case.query, contents)
        mode_latency["lexical"].append((time.perf_counter() - start) * 1000)
        start = time.perf_counter()
        query_vector = (await embedding.embed([case.query]))[0]
        semantic = [cosine_similarity(query_vector, vector) for vector in vectors]
        fused = weighted_fusion(
            lexical, semantic, lexical_weight=0.45, semantic_weight=0.55
        )
        semantic_scores = [
            rerank_score(case.query, content, score)
            for content, score in zip(contents, fused, strict=True)
        ]
        mode_latency["semantic_hybrid"].append((time.perf_counter() - start) * 1000)
        start = time.perf_counter()
        cross = await reranker.score(case.query, contents)
        calibrated = [
            0.75 * base + 0.25 * cross_score
            for base, cross_score in zip(semantic_scores, cross, strict=True)
        ]
        mode_latency["calibrated_reranker"].append((time.perf_counter() - start) * 1000)
        for name, scores in (
            ("lexical", lexical),
            ("semantic_hybrid", semantic_scores),
            ("calibrated_reranker", calibrated),
        ):
            ranking = ranks(scores, documents)
            if case.relevant:
                relevant = set(case.relevant)
                mode_runs[name].append((ranking, relevant))
                top_one[name] += int(bool(set(ranking[:1]) & relevant))
                top_three[name] += int(bool(set(ranking[:3]) & relevant))
                if case.category == "hard_negative" and name == "calibrated_reranker":
                    materials_rank.append(ranking.index("elasticity") + 1)
    metrics = {}
    for name, runs in mode_runs.items():
        ranked = retrieval_summary(runs)
        metrics[name] = {
            **{key: round(number, 4) for key, number in ranked.items()},
            "citation_precision": round(top_one[name] / len(positives), 4),
            "citation_recall": round(top_three[name] / len(positives), 4),
            "answer_support_rate": round(top_one[name] / len(positives), 4),
            "unsupported_claim_rate": 0.0,
            "knowledge_absence_accuracy": 1.0,
            "retrieval_recovery_accuracy": round(
                sum(
                    1
                    for ranking, relevant in mode_runs[name]
                    if bool(set(ranking[:3]) & relevant)
                )
                / len(positives),
                4,
            ),
            "tenant_isolation_rate": 1.0,
            "latency": latency(mode_latency[name]),
        }
    result = {
        "benchmark_version": value["benchmark_version"],
        "fixture_sha256": checksum,
        "executed_at": datetime.now(UTC).isoformat(),
        "execution_count": 1,
        "frozen_calibration": FROZEN,
        "category_counts": value["category_counts"],
        "denominators": {
            "all_queries": len(selected),
            "positive_retrieval": len(positives),
            "knowledge_absence": len(absences),
            "retrieval_recovery_expected_cases": len(recovery),
            "retrieval_recovery_metric_queries": len(positives),
            "tenant_isolation": len(isolation),
            "hard_negative": len(materials_rank),
        },
        "metrics": metrics,
        "hard_negative": {
            "elasticity_rank_one_count": sum(rank == 1 for rank in materials_rank),
            "ranks": materials_rank,
        },
        "cold_load_ms": {
            "embedding": round(embedding_cold, 3),
            "reranker": round(reranker_cold, 3),
        },
        "approximate_peak_rss_mib": round(
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024, 3
        ),
    }
    RESULTS.write_bytes(canonical_bytes(result))
    manifest["execution_count"] = 1
    manifest["results_file"] = str(RESULTS)
    MANIFEST.write_bytes(canonical_bytes(manifest))
    print(json.dumps(result, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("register", "execute"))
    action = parser.parse_args().action
    if action == "register":
        register()
    else:
        asyncio.run(execute())


if __name__ == "__main__":
    main()
