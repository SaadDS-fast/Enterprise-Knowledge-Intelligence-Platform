# Response-state consistency

Search, Controlled Agent, Evaluation, and Research share
`app.rag.response_state.CanonicalResponseState`. Every completed response has one
terminal `primary_state`: `SUPPORTED`, `SUPPORTED_COMPOSITE`,
`CONFLICTING_EVIDENCE`, `KNOWLEDGE_ABSENT`, `RETRIEVAL_FAILURE`,
`AMBIGUOUS_QUERY`, `LOW_QUALITY_SOURCE`, `INSUFFICIENT_EVIDENCE`,
`PROCESSING_FAILED`, or `CANCELLED`.

The contract also carries an evidence decision, typed conflict, claim-to-citation
mapping, component confidence bands, retrieval/recovery state, selected-document
scope, safe diagnostics, and a user-facing message. Search and Agent expose it as
`response_state`; Evaluation persists it per case and Research records it in report
generation metadata.

## Invariants and compatibility

The centralized validator checks answer presence, sufficient evidence, claim and
citation coverage, conflict sides, confidence compatibility, retrieval/fallback
compatibility, and selected-document authorization. Composite answers require at
least two cited components. Conflict responses require two cited, material,
unresolved sides. Absence, ambiguity, retrieval failure, failed, and cancelled
states cannot carry factual answer support.

Invalid combinations become a sanitized `PROCESSING_FAILED` response with
`response_invariant_violation`. Legacy `outcome`, `abstained`,
`sufficient_evidence`, `confidence_category`, and `answer` fields are compatibility
projections of the canonical state.

## Claims, conflicts, confidence, and presentation

Claims preserve original evidence text while normalizing subject, attribute, value,
unit, currency, date type, role, action, negation, policy version, applicability,
document status, and effective period where supported. `PKR 5,000 per day` and
`5,000 PKR daily` are equivalent. Annual revenue and annual budget, and publication
and effective dates, remain distinct attributes.

Conflict categories are `VALUE_CONFLICT`, `DATE_CONFLICT`, `ROLE_CONFLICT`,
`POLICY_RULE_CONFLICT`, `VERSION_CONFLICT`, `DEFINITION_CONFLICT`,
`SCOPE_CONFLICT`, and `NO_CONFLICT`. Current authoritative metadata resolves
superseded evidence without an unresolved conflict.

Confidence uses `HIGH`, `MEDIUM`, `LOW`, and `NOT_APPLICABLE` for retrieval,
evidence support, conflict detection, and the final response. Retrieval agreement,
rank/support signals, recovery, concept/value preservation, citation coverage,
source quality, version applicability, and unresolved conflicts inform the bands.
A supported answer is high or medium; conflict, absence, ambiguity, and retrieval
failure never become a high-confidence answer.

The frontend presents one human-readable primary status, compatible confidence and
retrieval details, selected-document scope, claim-linked citations, and separate
conflict sides. Technical retrieval diagnostics remain collapsible.
