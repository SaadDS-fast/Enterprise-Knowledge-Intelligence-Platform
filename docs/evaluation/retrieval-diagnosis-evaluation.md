# Retrieval Diagnosis Evaluation

Updated on 2026-07-20.

## Dataset

The deterministic dataset is stored at:

```text
docs/evaluation/retrieval-diagnosis-cases.json
```

It covers:

1. Initial retrieval succeeds.
2. Initial retrieval misses.
3. Retry retrieves the answer.
4. Answer is absent from the corpus.
5. Partial evidence exists.
6. Conflicting evidence exists.
7. Query is ambiguous.
8. Stopword overlap only.
9. Adversarial document content.
10. Similar documents in separate tenants.

## Metrics Helper

`backend/app/evaluation/retrieval_diagnosis.py` computes:

- diagnosis accuracy
- retry recovery rate
- knowledge-absence detection accuracy
- false knowledge-absence rate
- false retrieval-failure rate
- abstention accuracy
- false abstention rate
- average retrieval attempts

## Measured Results

The metric helper is covered by unit tests. A full corpus-backed evaluation run against PostgreSQL/pgvector was not executed because Docker/PostgreSQL is unavailable on this machine.
