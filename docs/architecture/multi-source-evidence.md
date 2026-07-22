# Multi-Source Evidence Architecture

Updated on 2026-07-22.

## Scope

The controlled agent aggregates evidence from authorized internal documents and optional approved external sources. External access remains disabled by default, feature-flag controlled, and opt-in per request.

Supported source types:

- `internal_document`
- `web_search`
- `wikipedia`
- `arxiv`
- `approved_api`

## Unified Evidence

All sources are normalized into a Pydantic-validated `UnifiedEvidence` model before ranking or synthesis. Internal evidence carries tenant, workspace, document, document-version, and chunk scope when available. External evidence never carries tenant or workspace IDs and is always marked `untrusted_external_content=true`.

The model includes source type, provider, title, excerpt, canonical URL, internal IDs, retrieval/reranker/trust/freshness/combined scores, retrieval timestamp, publication metadata, citation label, and deduplication metadata. Full webpage content is not stored.

Malformed normalized evidence is rejected rather than silently accepted.

## Deduplication

Deduplication uses scoped internal identity, canonical external URL, normalized title, and excerpt fingerprinting. Internal evidence is never merged across different tenants or workspaces. Merge metadata records `duplicate_count`, `merged_source_ids`, and `retained_evidence_id`.

## Ranking

Ranking uses deterministic Reciprocal Rank Fusion with source-aware weights:

- `EVIDENCE_RRF_K=60`
- `EVIDENCE_INTERNAL_PRIORITY_WEIGHT=1.0`
- `EVIDENCE_EXTERNAL_TRUST_WEIGHT=0.8`
- `EVIDENCE_MIN_SUPPORT_SCORE=0.65`

Internal evidence remains preferred for organization-specific questions. Freshness affects only time-sensitive queries such as latest/current/recent questions. Trust weights are configurable through `EVIDENCE_TRUST_WEIGHTS`.

## Context Budget

The context budget manager caps total evidence, internal evidence, external evidence, and excerpt characters:

- `EVIDENCE_MAX_ITEMS=12`
- `EVIDENCE_MAX_INTERNAL_ITEMS=8`
- `EVIDENCE_MAX_EXTERNAL_ITEMS=6`
- `EVIDENCE_CONTEXT_MAX_CHARS=12000`

It preserves citation mapping, source diversity, and conflicting evidence relevant to the query. Citation labels are renumbered after truncation so labels remain valid.

## Claim Verification

The deterministic verifier extracts factual claims from selected evidence and records:

- `SUPPORTED`
- `PARTIALLY_SUPPORTED`
- `UNSUPPORTED`
- `CONFLICTED`
- `NOT_VERIFIABLE`

Unsupported claims are removed or cause abstention. Supported claims must cite actual evidence. The verifier is deterministic by default; the provider interface leaves room for future Ollama-based verification without making Ollama mandatory.

## Conflict Detection

The verifier detects practical conflicts for numeric values, dates, opposing statuses, owner/entity differences, and negation. Outcomes are:

- `NO_CONFLICT`
- `POSSIBLE_CONFLICT`
- `CONFIRMED_CONFLICT`

Confirmed conflicts are not silently resolved. The response cites both sides and asks for clarification when necessary.

## Citation Validation

Citation validation checks that every label resolves to retained evidence, citations are used by a verified claim, internal scope is authorized, external URLs were normalized from validated providers, duplicates are removed, and unrelated labels are rejected.

Internal citations include document title, version when available, page or section when available, chunk ID, and excerpt. External citations include provider, title, canonical URL, retrieval date, and excerpt.

## Response Outcome

The agent response now includes:

- `outcome`
- `claims`
- `conflicts`
- `unsupported_claims_removed`
- `confidence_category`
- `unified_evidence`
- `evidence_ranking`
- `evidence_deduplication`
- `context_budget`

Outcomes are `ANSWER_SUPPORTED`, `ANSWER_PARTIALLY_SUPPORTED`, `CONFLICTING_EVIDENCE`, `INSUFFICIENT_EVIDENCE`, `KNOWLEDGE_ABSENT`, `CLARIFICATION_REQUIRED`, `SAFETY_BLOCKED`, and `FAILED`.
