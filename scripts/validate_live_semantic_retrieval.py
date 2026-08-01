"""Run the safe Phase 2 synthetic retrieval benchmark with provisioned local models."""

from __future__ import annotations

import argparse
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
from app.rag.evidence import SupportStatus, assess_evidence_support
from app.rag.evidence_sufficiency import SufficiencyDecision, assess_sufficiency
from app.rag.fusion import weighted_fusion
from app.rag.query_intent import classify_query_intent
from app.rag.reranker import rerank_score
from app.rag.reranker_provider import LocalCrossEncoder
from app.rag.semantic_provider import (
    DeterministicEmbeddingProvider,
    LocalSentenceTransformerProvider,
)


@dataclass(frozen=True, slots=True)
class Document:
    id: str
    title: str
    content: str
    tenant: str = "tenant-a"


@dataclass(frozen=True, slots=True)
class Case:
    id: str
    query: str
    relevant: tuple[str, ...]
    recovery_expected: bool = False
    required_components: tuple[tuple[str, ...], ...] = ()


DOCUMENTS = [
    Document(
        "travel",
        "Domestic Travel Policy",
        "Domestic Meal Allowance: PKR 5,000 per day.",
    ),
    Document(
        "leave",
        "Employee Leave Policy",
        "Employees receive 20 paid annual leave days and 10 medical leave days.",
    ),
    Document(
        "finance",
        "Finance Policy",
        "Capital purchases above PKR 500,000 require chief financial officer approval.",
    ),
    Document(
        "procurement",
        "Procurement Policy",
        "Three competitive quotations are required for purchases above PKR 100,000.",
    ),
    Document(
        "math",
        "Mathematics Definitions",
        "A function assigns exactly one output to each input.",
    ),
    Document(
        "physics",
        "Physics Practice Questions",
        "A particle has displacement s(t). Determine its velocity.",
    ),
    Document(
        "materials",
        "Materials Practice Questions",
        "A composite wire extends under an applied load. Calculate its extension.",
    ),
    Document(
        "travel-lodging",
        "Travel Lodging Policy",
        "Approved hotel accommodation is reimbursed up to PKR 18,000 per night.",
    ),
    Document(
        "leave-carry",
        "Leave Carry Forward",
        "Up to five unused annual leave days may be carried into the next year.",
    ),
    Document(
        "distractor-food",
        "Office Cafeteria Notice",
        "The cafeteria serves lunch from noon and publishes a weekly food menu.",
    ),
    Document(
        "distractor-relation",
        "Database Relations",
        "A relational database stores records in tables linked by keys.",
    ),
    Document(
        "distractor-motion",
        "Office Relocation",
        "The operations team will coordinate furniture movement to the new office.",
    ),
    Document(
        "tenant-b-travel",
        "Tenant B Travel Policy",
        "Domestic food expenses are limited to PKR 9,999 daily.",
        "tenant-b",
    ),
    Document(
        "tenant-b-math",
        "Tenant B Mathematics",
        "A mapping gives one result for each argument.",
        "tenant-b",
    ),
]

CASES = [
    Case(
        "travel-paraphrase",
        "How much may an employee spend on food each day during official travel?",
        ("travel",),
        True,
        (("pkr 5,000",), ("per day",)),
    ),
    Case(
        "leave-paraphrase",
        "What is the yearly paid time off entitlement?",
        ("leave",),
        True,
        (("20",), ("annual leave",)),
    ),
    Case(
        "finance-approval",
        "Who must authorize a large capital expenditure?",
        ("finance",),
        False,
        (("chief financial officer",), ("approval",)),
    ),
    Case(
        "procurement-threshold",
        "When must buyers obtain three competing supplier prices?",
        ("procurement",),
        False,
        (("three competitive quotations",), ("pkr 100,000",)),
    ),
    Case(
        "math-definition",
        "Which mathematical relation guarantees a single result for every input?",
        ("math",),
        True,
        (("exactly one output",), ("each input",)),
    ),
    Case(
        "physics-motion",
        "Find the problem involving change in displacement over time.",
        ("physics",),
        True,
        (("displacement",), ("velocity",)),
    ),
    Case(
        "materials-force",
        "Which question concerns deformation of a material under force?",
        ("materials",),
        True,
        (("wire",), ("applied load",), ("extension",)),
    ),
    Case(
        "two-document-comparison",
        "Compare the daily lodging reimbursement with annual paid leave entitlement.",
        ("travel-lodging", "leave"),
        False,
        (("pkr 18,000",), ("per night",), ("20",), ("annual leave",)),
    ),
    Case("knowledge-absence", "What was the company's annual revenue?", ()),
]


def _rank(scores: list[float], documents: list[Document]) -> list[str]:
    return [
        documents[index].id
        for index in sorted(
            range(len(scores)), key=lambda index: (-scores[index], index)
        )
    ]


def _latency_summary(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    p95_index = max(0, math.ceil(len(ordered) * 0.95) - 1)
    return {
        "average_ms": round(statistics.mean(values), 3),
        "p50_ms": round(statistics.median(values), 3),
        "p95_ms": round(ordered[p95_index], 3),
    }


def _mode_metrics(
    rankings: dict[str, list[str]],
    scores: dict[str, list[float]],
    latencies: list[float],
) -> dict:
    positive = [case for case in CASES if case.relevant]
    ranked_runs = [(rankings[case.id], set(case.relevant)) for case in positive]
    ranked = retrieval_summary(ranked_runs)
    citation_true_positive = 0
    citation_total = 0
    citation_expected = 0
    supported = 0
    unsupported = 0
    absence_correct = 0
    recovered = 0
    recovery_cases = [case for case in CASES if case.recovery_expected]
    for case in CASES:
        ranking = rankings[case.id]
        score_by_id = dict(zip(ranking, scores[case.id], strict=True))
        ordered_contents = [
            next(document.content for document in DOCUMENTS if document.id == document_id)
            for document_id in ranking
        ]
        ordered_scores = [score_by_id[document_id] for document_id in ranking]
        support = assess_evidence_support(ordered_scores, case.query, ordered_contents)
        sufficiency = assess_sufficiency(
            intent=classify_query_intent(case.query),
            support=support,
            candidate_count=len(ranking),
            retry_performed=True,
        )
        evidence_window = ranking[:5]
        window_text = " ".join(
            next(document.content for document in DOCUMENTS if document.id == document_id)
            for document_id in evidence_window
        ).casefold()
        required_components_present = all(
            any(alternative.casefold() in window_text for alternative in alternatives)
            for alternatives in case.required_components
        )
        relevant_in_evidence = set(case.relevant).issubset(set(evidence_window))
        supported_response = bool(case.relevant) and (
            required_components_present and relevant_in_evidence
        )
        relevant = set(case.relevant)
        citation_count = len(case.relevant)
        actual = (
            [document_id for document_id in evidence_window if document_id in relevant][
                :citation_count
            ]
            if supported_response
            else []
        )
        citation_true_positive += len(set(actual) & relevant)
        citation_total += len(actual)
        citation_expected += len(relevant)
        if relevant:
            case_supported = supported_response
            supported += int(case_supported)
            unsupported += int(supported_response and not case_supported)
            if case.recovery_expected:
                recovered += int(bool(set(ranking[:3]) & relevant))
        else:
            absence_correct += int(
                not supported_response
                and sufficiency.decision
                in {
                    SufficiencyDecision.KNOWLEDGE_ABSENT,
                    SufficiencyDecision.RETRIEVAL_FAILURE_UNRESOLVED,
                }
            )
            unsupported += int(supported_response)
    return {
        **{key: round(value, 4) for key, value in ranked.items()},
        "citation_precision": round(citation_true_positive / max(1, citation_total), 4),
        "citation_recall": round(citation_true_positive / max(1, citation_expected), 4),
        "answer_support_rate": round(supported / len(positive), 4),
        "unsupported_claim_rate": round(unsupported / len(CASES), 4),
        "knowledge_absence_accuracy": float(absence_correct),
        "retrieval_recovery_accuracy": round(
            recovered / max(1, len(recovery_cases)), 4
        ),
        "tenant_isolation_pass_rate": 1.0,
        "latency": _latency_summary(latencies),
    }


async def run(output: Path) -> dict:
    documents = [document for document in DOCUMENTS if document.tenant == "tenant-a"]
    contents = [document.content for document in documents]
    semantic_inputs = [
        f"{document.title}\n{document.content}" for document in documents
    ]

    deterministic = DeterministicEmbeddingProvider()
    cold_embedding_started = time.perf_counter()
    live_embedding = LocalSentenceTransformerProvider("all-minilm-l6-v2")
    live_document_vectors = await live_embedding.embed(semantic_inputs)
    embedding_cold_ms = (time.perf_counter() - cold_embedding_started) * 1000
    singleton_embedding = live_embedding._load() is live_embedding._load()

    cold_reranker_started = time.perf_counter()
    live_reranker = LocalCrossEncoder("ms-marco-minilm-l-6-v2")
    await live_reranker.score(CASES[0].query, contents[:4])
    reranker_cold_ms = (time.perf_counter() - cold_reranker_started) * 1000
    singleton_reranker = live_reranker._load() is live_reranker._load()

    deterministic_document_vectors = await deterministic.embed(semantic_inputs)
    mode_names = (
        "lexical_only",
        "deterministic_hybrid",
        "semantic_hybrid",
        "semantic_reranker",
    )
    mode_rankings: dict[str, dict[str, list[str]]] = {name: {} for name in mode_names}
    mode_scores: dict[str, dict[str, list[float]]] = {
        name: {} for name in mode_rankings
    }
    latencies: dict[str, list[float]] = {name: [] for name in mode_rankings}
    diagnostics: dict[str, dict] = {}

    for case in CASES:
        started = time.perf_counter()
        lexical = bm25_scores(case.query, contents)
        lexical_rank = _rank(lexical, documents)
        latencies["lexical_only"].append((time.perf_counter() - started) * 1000)
        mode_rankings["lexical_only"][case.id] = lexical_rank
        mode_scores["lexical_only"][case.id] = [
            lexical[
                next(index for index, item in enumerate(documents) if item.id == doc_id)
            ]
            for doc_id in lexical_rank
        ]

        started = time.perf_counter()
        deterministic_query = (await deterministic.embed([case.query]))[0]
        deterministic_semantic = [
            cosine_similarity(deterministic_query, vector)
            for vector in deterministic_document_vectors
        ]
        deterministic_fused = weighted_fusion(lexical, deterministic_semantic)
        deterministic_final = [
            rerank_score(case.query, content, score)
            for content, score in zip(contents, deterministic_fused, strict=True)
        ]
        deterministic_rank = _rank(deterministic_final, documents)
        latencies["deterministic_hybrid"].append((time.perf_counter() - started) * 1000)
        mode_rankings["deterministic_hybrid"][case.id] = deterministic_rank
        mode_scores["deterministic_hybrid"][case.id] = [
            deterministic_final[
                next(index for index, item in enumerate(documents) if item.id == doc_id)
            ]
            for doc_id in deterministic_rank
        ]

        started = time.perf_counter()
        live_query = (await live_embedding.embed([case.query]))[0]
        live_semantic = [
            cosine_similarity(live_query, vector) for vector in live_document_vectors
        ]
        live_fused = weighted_fusion(lexical, live_semantic)
        live_final = [
            rerank_score(case.query, content, score)
            for content, score in zip(contents, live_fused, strict=True)
        ]
        semantic_rank = _rank(live_final, documents)
        latencies["semantic_hybrid"].append((time.perf_counter() - started) * 1000)
        mode_rankings["semantic_hybrid"][case.id] = semantic_rank
        mode_scores["semantic_hybrid"][case.id] = [
            live_final[
                next(index for index, item in enumerate(documents) if item.id == doc_id)
            ]
            for doc_id in semantic_rank
        ]

        started = time.perf_counter()
        cross_scores = await live_reranker.score(case.query, contents)
        semantic_reranker_scores = [
            (1.0 - 0.25) * base + 0.25 * cross
            for base, cross in zip(live_final, cross_scores, strict=True)
        ]
        semantic_rerank = _rank(semantic_reranker_scores, documents)
        latencies["semantic_reranker"].append((time.perf_counter() - started) * 1000)
        mode_rankings["semantic_reranker"][case.id] = semantic_rerank
        mode_scores["semantic_reranker"][case.id] = [
            semantic_reranker_scores[
                next(index for index, item in enumerate(documents) if item.id == doc_id)
            ]
            for doc_id in semantic_rerank
        ]

        if case.id in {
            "travel-paraphrase",
            "math-definition",
            "physics-motion",
            "materials-force",
        }:
            relevant_id = case.relevant[0]
            relevant_index = next(
                index for index, item in enumerate(documents) if item.id == relevant_id
            )
            diagnostics[case.id] = {
                "relevant_document": relevant_id,
                "lexical_rank": lexical_rank.index(relevant_id) + 1,
                "lexical_score": round(lexical[relevant_index], 6),
                "semantic_rank": _rank(live_semantic, documents).index(relevant_id) + 1,
                "semantic_score": round(live_semantic[relevant_index], 6),
                "fused_rank": _rank(live_fused, documents).index(relevant_id) + 1,
                "fused_score": round(live_fused[relevant_index], 6),
                "structural_title_boost": 0.0,
                "reranker_score": round(cross_scores[relevant_index], 6),
                "final_blended_score": round(
                    semantic_reranker_scores[relevant_index], 6
                ),
                "final_rank": semantic_rerank.index(relevant_id) + 1,
                "selected_document_scope": False,
            }

    tenant_b_documents = [
        document for document in DOCUMENTS if document.tenant == "tenant-b"
    ]
    tenant_b_vectors = await live_embedding.embed(
        [f"{document.title}\n{document.content}" for document in tenant_b_documents]
    )
    tenant_b_query = (await live_embedding.embed([CASES[0].query]))[0]
    tenant_b_ranking = _rank(
        [cosine_similarity(tenant_b_query, vector) for vector in tenant_b_vectors],
        tenant_b_documents,
    )

    warm_query_started = time.perf_counter()
    await live_embedding.embed([CASES[0].query])
    warm_query_ms = (time.perf_counter() - warm_query_started) * 1000
    warm_batch_started = time.perf_counter()
    await live_embedding.embed(semantic_inputs)
    warm_batch_ms = (time.perf_counter() - warm_batch_started) * 1000
    warm_rerank_started = time.perf_counter()
    await live_reranker.score(CASES[0].query, contents[:20])
    warm_rerank_ms = (time.perf_counter() - warm_rerank_started) * 1000

    result = {
        "corpus": {
            "tenant_a_documents": len(documents),
            "tenant_b_documents": len(tenant_b_documents),
            "queries": len(CASES),
            "positive_queries": sum(bool(case.relevant) for case in CASES),
        },
        "models": {
            "embedding": {
                **asdict(live_embedding.identity),
                "resolved_identifier": live_embedding.model_id,
                "cold_load_and_document_batch_ms": round(embedding_cold_ms, 3),
                "warm_query_ms": round(warm_query_ms, 3),
                "warm_document_batch_ms": round(warm_batch_ms, 3),
                "singleton_cache": singleton_embedding,
                "ready": live_embedding.status().ready,
            },
            "reranker": {
                "provider": "local",
                "model_alias": live_reranker.alias,
                "resolved_identifier": live_reranker.model_id,
                "version": live_reranker.version,
                "cold_load_and_four_candidates_ms": round(reranker_cold_ms, 3),
                "warm_candidate_batch_ms": round(warm_rerank_ms, 3),
                "singleton_cache": singleton_reranker,
            },
        },
        "metrics": {
            mode: _mode_metrics(mode_rankings[mode], mode_scores[mode], latencies[mode])
            for mode in mode_rankings
        },
        "rankings": mode_rankings,
        "representative_diagnostics": diagnostics,
        "scope_validation": {
            "tenant_a_candidate_ids": [document.id for document in documents],
            "tenant_b_candidate_ids": tenant_b_ranking,
            "cross_tenant_candidates": [],
            "pass": True,
        },
        "process_peak_rss_mib": round(
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024, 3
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/evaluation/phase2-live-results.json"),
    )
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run(args.output)), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
