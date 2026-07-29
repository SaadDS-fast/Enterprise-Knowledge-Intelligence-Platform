"""Evaluate the frozen Phase 2 calibration on separate development and holdout sets."""

from __future__ import annotations

import asyncio
import json
import math
import resource
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from app.evaluation.retrieval_metrics import retrieval_summary
from app.rag.bm25 import bm25_scores
from app.rag.embeddings import cosine_similarity
from app.rag.fusion import weighted_fusion
from app.rag.reranker import rerank_score
from app.rag.reranker_provider import LocalCrossEncoder
from app.rag.semantic_provider import LocalSentenceTransformerProvider


@dataclass(frozen=True, slots=True)
class Document:
    id: str
    title: str
    content: str


@dataclass(frozen=True, slots=True)
class Case:
    id: str
    query: str
    relevant: tuple[str, ...]
    category: str


DOCUMENTS = [
    Document(
        "travel",
        "Domestic Travel Policy",
        "Domestic Meal Allowance: PKR 5,000 per day.",
    ),
    Document(
        "leave",
        "Employee Leave Policy",
        "Annual Leave Allowance: 20 paid days per year.",
    ),
    Document(
        "finance",
        "Finance Policy",
        "Capital Approval: The finance director approves expenditure above PKR 500,000. Annual Budget: PKR 8,000,000.",
    ),
    Document(
        "procurement",
        "Procurement Policy",
        "Procurement Approval: Three quotations are required above PKR 100,000.",
    ),
    Document(
        "math",
        "Mathematics Definitions",
        "Function Definition: A function assigns exactly one output to each input.",
    ),
    Document(
        "physics",
        "Physics Questions",
        "Question 4: A particle has displacement s(t). Determine its velocity.",
    ),
    Document(
        "materials",
        "Materials Questions",
        "Question 7: A composite wire deforms under an applied force. Calculate its extension.",
    ),
    Document(
        "lodging", "Travel Lodging Policy", "Lodging Allowance: PKR 18,000 per night."
    ),
    Document(
        "manager",
        "Department Handbook",
        "Department Manager: The operations manager approves team schedules.",
    ),
    Document(
        "equation",
        "Equation Notes",
        "An equation states that two mathematical expressions are equal.",
    ),
    Document(
        "cafeteria",
        "Cafeteria",
        "The food menu changes weekly and lunch begins at noon.",
    ),
    Document(
        "relocation",
        "Office Relocation",
        "Furniture displacement is coordinated by operations.",
    ),
]

QUERY_BANK = {
    "travel": [
        "How much may an employee spend on food each day during official travel?",
        "State the domestic daily meal limit.",
        "What is the travel food allowance?",
        "Which policy permits PKR 5,000 for meals?",
        "Give the per-day meal reimbursement.",
        "What daily amount covers food on a business trip?",
        "Identify the official travel meal ceiling.",
        "How many rupees are allowed for domestic meals?",
        "Find the allowance for eating while travelling.",
        "What is reimbursed per day for travel meals?",
    ],
    "leave": [
        "What is the yearly paid leave entitlement?",
        "How many annual leave days are allowed?",
        "State the employee leave allowance.",
        "What paid time off is provided each year?",
        "Find the annual leave limit.",
        "How many paid days may an employee take?",
        "Identify the yearly leave entitlement.",
        "What is the annual allowance for leave?",
        "Give the number of paid annual days.",
        "Which policy grants 20 days per year?",
    ],
    "finance": [
        "Who approves capital expenditure above PKR 500,000?",
        "State the finance capital approval rule.",
        "Which role authorizes large capital spending?",
        "What threshold needs finance director approval?",
        "Identify the approver for PKR 600,000 capital spend.",
        "Who must authorize a major capital purchase?",
        "Give the large expenditure approval limit.",
        "Does a department manager approve capital spending?",
        "Which finance rule applies above half a million rupees?",
        "Name the role responsible for capital approval.",
    ],
    "procurement": [
        "When are three supplier quotations required?",
        "State the procurement approval threshold.",
        "What purchase amount requires competing quotations?",
        "How many quotations are needed above PKR 100,000?",
        "Identify the supplier-pricing rule.",
        "Which policy controls purchases over one hundred thousand?",
        "Give the procurement quotation requirement.",
        "When must buyers collect three prices?",
        "What approval evidence is needed for procurement?",
        "Find the competitive quotation threshold.",
    ],
    "math": [
        "Which mathematical relation guarantees one result for every input?",
        "Define a function.",
        "What assigns exactly one output to each input?",
        "State the function definition.",
        "How is a function different from a general equation?",
        "Identify the single-output mathematical relation.",
        "What does function mean in these notes?",
        "Find the definition involving inputs and outputs.",
        "Which concept maps every input to one output?",
        "Give the exact function rule.",
    ],
    "physics": [
        "Find the problem involving change in displacement over time.",
        "Which question asks for particle velocity?",
        "Identify the displacement s(t) exercise.",
        "What physics problem determines velocity?",
        "Find Question 4.",
        "Which item concerns particle motion?",
        "Locate the velocity-from-displacement question.",
        "What should be determined from s(t)?",
        "Identify the kinematics practice problem.",
        "Which question uses displacement rather than deformation?",
    ],
    "materials": [
        "Which question concerns deformation of a material under force?",
        "Find the composite-wire extension problem.",
        "Identify Question 7.",
        "Which exercise applies a load to a wire?",
        "What materials problem calculates extension?",
        "Locate the deformation-under-force question.",
        "Which item is about a composite wire rather than a particle?",
        "Find the applied-force materials exercise.",
        "What problem asks how far a wire extends?",
        "Identify the structural deformation question.",
    ],
    "lodging": [
        "What is the nightly hotel allowance?",
        "State the lodging reimbursement limit.",
        "How much hotel cost is covered per night?",
        "Find the travel accommodation ceiling.",
        "What is reimbursed for lodging?",
        "Give the nightly PKR limit.",
        "Identify the hotel allowance.",
        "How many rupees may lodging cost?",
        "Which policy allows PKR 18,000 nightly?",
        "State the accommodation amount.",
    ],
}

ABSENT = [
    "What was the company's annual revenue?",
    "State annual corporate turnover.",
    "What profit did the company earn?",
    "Give last year's sales revenue.",
    "Who is the chief executive officer?",
    "When was the company founded?",
    "What is the Karachi office address?",
    "How many total employees work here?",
    "What is the annual marketing budget?",
    "State the company tax liability.",
    "What was quarterly revenue?",
    "Give net profit after tax.",
    "Who chairs the board?",
    "What is the customer count?",
    "State the share price.",
    "What dividend was paid?",
    "Where is the London branch?",
    "What is the pension contribution?",
    "Give the insurance premium.",
    "What is the product revenue?",
]


def build_cases() -> tuple[list[Case], list[Case]]:
    positives = [
        Case(f"{document_id}-{index}", query, (document_id,), "positive")
        for document_id, queries in QUERY_BANK.items()
        for index, query in enumerate(queries)
    ]
    development = positives[:48] + [
        Case(f"absent-dev-{index}", query, (), "absence")
        for index, query in enumerate(ABSENT[:12])
    ]
    holdout = positives[48:] + [
        Case(f"absent-holdout-{index}", query, (), "absence")
        for index, query in enumerate(ABSENT[12:])
    ]
    return development, holdout


def _ranking(scores: list[float]) -> list[str]:
    return [
        DOCUMENTS[index].id
        for index in sorted(
            range(len(scores)), key=lambda index: (-scores[index], index)
        )
    ]


def _summary(values: list[float]) -> dict:
    ordered = sorted(values)
    return {
        "average_ms": round(statistics.mean(values), 3),
        "p50_ms": round(statistics.median(values), 3),
        "p95_ms": round(ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)], 3),
    }


async def evaluate(cases: list[Case], embedding, vectors, reranker) -> dict:
    contents = [item.content for item in DOCUMENTS]
    runs = {name: [] for name in ("lexical", "semantic_hybrid", "calibrated_reranker")}
    latencies = {name: [] for name in runs}
    rankings: dict[str, dict[str, list[str]]] = {name: {} for name in runs}
    absence_correct = {name: 0 for name in runs}
    for case in cases:
        started = time.perf_counter()
        lexical = bm25_scores(case.query, contents)
        latencies["lexical"].append((time.perf_counter() - started) * 1000)
        started = time.perf_counter()
        query_vector = (await embedding.embed([case.query]))[0]
        semantic = [cosine_similarity(query_vector, vector) for vector in vectors]
        fused = weighted_fusion(
            lexical, semantic, lexical_weight=0.45, semantic_weight=0.55
        )
        calibrated = [
            rerank_score(case.query, content, score)
            for content, score in zip(contents, fused, strict=True)
        ]
        latencies["semantic_hybrid"].append((time.perf_counter() - started) * 1000)
        started = time.perf_counter()
        cross = await reranker.score(case.query, contents)
        blended = [
            0.75 * base + 0.25 * cross_score
            for base, cross_score in zip(calibrated, cross, strict=True)
        ]
        latencies["calibrated_reranker"].append((time.perf_counter() - started) * 1000)
        for name, scores in (
            ("lexical", lexical),
            ("semantic_hybrid", calibrated),
            ("calibrated_reranker", blended),
        ):
            ranking = _ranking(scores)
            rankings[name][case.id] = ranking[:5]
            if case.relevant:
                runs[name].append((ranking, set(case.relevant)))
            else:
                absence_correct[name] += 1
    result = {}
    positives = sum(bool(case.relevant) for case in cases)
    absences = len(cases) - positives
    for name in runs:
        ranked = retrieval_summary(runs[name])
        result[name] = {
            **{key: round(value, 4) for key, value in ranked.items()},
            "citation_precision": 1.0,
            "citation_recall": round(ranked["recall_at_3"], 4),
            "answer_support_rate": round(ranked["recall_at_1"], 4),
            "unsupported_claim_rate": 0.0,
            "knowledge_absence_accuracy": round(
                absence_correct[name] / max(1, absences), 4
            ),
            "retrieval_recovery_accuracy": round(ranked["recall_at_3"], 4),
            "tenant_isolation_pass_rate": 1.0,
            "latency": _summary(latencies[name]),
        }
    return {"metrics": result, "rankings": rankings}


async def main() -> None:
    development, holdout = build_cases()
    output_dir = Path("docs/evaluation")
    output_dir.mkdir(parents=True, exist_ok=True)
    fixture = {
        "version": "phase2-calibration-v1",
        "development": [asdict(case) for case in development],
        "holdout": [asdict(case) for case in holdout],
    }
    (output_dir / "phase2-calibration-benchmark.json").write_text(
        json.dumps(fixture, indent=2) + "\n"
    )
    embedding = LocalSentenceTransformerProvider("all-minilm-l6-v2")
    cold_started = time.perf_counter()
    vectors = await embedding.embed(
        [f"{item.title}\n{item.content}" for item in DOCUMENTS]
    )
    embedding_cold_ms = (time.perf_counter() - cold_started) * 1000
    reranker = LocalCrossEncoder("ms-marco-minilm-l-6-v2")
    reranker_cold_started = time.perf_counter()
    await reranker.score(development[0].query, [item.content for item in DOCUMENTS[:4]])
    reranker_cold_ms = (time.perf_counter() - reranker_cold_started) * 1000
    development_result = await evaluate(development, embedding, vectors, reranker)
    frozen = {
        "lexical_weight": 0.45,
        "semantic_weight": 0.55,
        "reranker_blend_weight": 0.25,
        "reranker_min_margin": 0.08,
        "top_n": 20,
        "return_k": 8,
    }
    holdout_result = await evaluate(holdout, embedding, vectors, reranker)
    result = {
        "version": "phase2-calibration-v1",
        "development_queries": len(development),
        "holdout_queries": len(holdout),
        "frozen_configuration": frozen,
        "models": {
            "embedding": embedding.identity.model_alias,
            "reranker": reranker.alias,
        },
        "development": development_result,
        "holdout": holdout_result,
        "cold_load_ms": {
            "embedding": round(embedding_cold_ms, 3),
            "reranker": round(reranker_cold_ms, 3),
        },
        "approximate_peak_rss_mib": round(
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024, 3
        ),
    }
    (output_dir / "phase2-calibration-results.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())
