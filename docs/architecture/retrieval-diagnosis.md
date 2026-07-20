# Retrieval Diagnosis

Updated on 2026-07-20.

## Purpose

The retrieval diagnosis component distinguishes these outcomes without using an unrestricted LLM as the classifier:

- `SUFFICIENT_EVIDENCE`
- `RETRIEVAL_FAILURE_RECOVERED`
- `RETRIEVAL_FAILURE_UNRESOLVED`
- `KNOWLEDGE_ABSENT`
- `PARTIAL_EVIDENCE`
- `CONFLICTING_EVIDENCE`
- `AMBIGUOUS_QUERY`

## Flow

```text
User query
-> prompt-safety scan
-> initial hybrid retrieval with tenant/workspace/document filters
-> evidence sufficiency check
-> if insufficient:
   -> deterministic query reformulation
   -> top-k expansion
   -> second retrieval with the same authorization filters
-> evidence merge and second sufficiency check
-> diagnosis from explainable signals
-> answer, abstention, or clarification-style result
```

The retry path never relaxes tenant, workspace, document, or prompt-security filters.

## Signals

- query key-term coverage
- best retrieval score
- evidence count
- support-score improvement after retry
- ambiguity from low-information queries
- conflict signals for date/budget queries
- final sufficiency decision

The API returns operational metadata in `retrieval_diagnosis`. It does not expose hidden reasoning, prompts, database internals, secrets, or authorization details.

## Frontend Display

The frontend maps diagnosis statuses to user-facing messages:

- Evidence found directly
- Evidence found after an additional search
- Relevant evidence may exist, but the search could not verify it
- Information does not appear to exist in the selected documents
- Only partial evidence found
- Conflicting evidence found
- Question needs clarification
