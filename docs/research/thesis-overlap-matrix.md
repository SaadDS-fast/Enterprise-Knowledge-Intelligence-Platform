# Thesis-overlap screening matrix

Status: mandatory design gate, 2026-08-01.

## Firewall rule

All candidates must preserve the runtime sequence:

`one configured retrieval pass → static support gate → supported answer OR neutral refusal`

Nothing after insufficient support may diagnose the condition, retry, reformulate, change Top-K,
select another retriever, recover evidence, allocate more retrieval budget, or expose a technical
reason. This document deliberately states only product boundaries and discloses no unpublished
method.

## Candidate decisions

| Candidate | Overlap level | Potentially overlapping component | Required safe redesign | Decision |
|---|---|---|---|---|
| A. Verifiable Answer Passport | None after constraints | A verifier might be misused to regenerate or “repair” an invalid artifact. | Issue only after an existing supported answer; verifier is pure validation and never calls search or generation. | **Accept** |
| B. Validity expiry / freshness | Low | A stale state could trigger automatic evidence refresh or explain insufficiency. | Compare signed timestamps/checksums/versions only; report `fresh`, `expired`, `version_mismatch`, or `unknown`; human starts any new independent query. | Accept as later passport policy; reject standalone now |
| C. Document-change impact | Medium | Impact detection could become evidence recovery, re-answering, or cause attribution. | Compare stored claim/span identifiers to supplied versions only; mark `review_required`; prohibit automatic search, replacement evidence, or diagnosis. | Reject first release; reconsider only with hard isolation |
| D. Policy comparison workspace | Low | The system could expand search when one side lacks support. | Require an authorized, user-selected document set before the ordinary single pass; neutral refusal remains terminal. | Accept boundary; defer product |
| E. Compliance evidence package | None after constraints | A package builder could search for missing controls/evidence. | Package only already-authorized, already-supported artifacts; omissions remain omissions and are not diagnosed or recovered. | Accept boundary; defer product |
| F. Grounded Decision Ledger | None | A reviewer workflow might request automatic re-grounding after rejection. | Ledger records answer/decision/approval/supersession events only; a new query is a separate explicit user action. | Accept boundary; runner-up |

## Explicit prohibited-mechanism test

| Candidate | Diagnose weak retrieval | Diagnose absent knowledge | Post-failure retry | Reformulate | Dynamic Top-K | Adaptive retriever | Evidence recovery | Failure-type mitigation |
|---|---|---|---|---|---|---|---|---|
| A | No | No | No | No | No | No | No | No |
| B (redesigned) | No | No | No | No | No | No | No | No |
| C (redesigned concept only) | No | No | No | No | No | No | No | No |
| D (bounded) | No | No | No | No | No | No | No | No |
| E (bounded) | No | No | No | No | No | No | No | No |
| F | No | No | No | No | No | No | No | No |

“No” is a normative requirement, not merely the current proposal’s intention. A future design that
changes any cell to “Yes” automatically fails this screen and requires rejection, not a waiver.

## Enforcement gates for future implementation

1. Passport issuance accepts an immutable supported-answer projection, never a query.
2. The verifier package has no dependency on retriever, LLM, search API, connector, or network
   client.
3. Refused responses cannot be passported.
4. Freshness and change results are integrity/lifecycle states, not explanations of retrieval
   performance.
5. A new answer requires a new explicit request through the unchanged ordinary pipeline.
6. Static architecture/import tests must reject dependencies from passport modules into retrieval
   or generation packages.
7. UI copy must not translate refusal into a cause, taxonomy, or suggested recovery tactic.

## Result

Candidate A clears the firewall as a strictly post-support assurance layer. Candidate C is the
closest boundary risk and is excluded from the recommended implementation. No candidate is allowed
to modify the existing neutral-refusal path.
