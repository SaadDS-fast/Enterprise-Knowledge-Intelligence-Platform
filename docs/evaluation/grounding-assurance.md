# Grounding assurance

The deterministic `grounding-assurance-v1` corpus contains 300 fictional documents and an
exact gold registry. The 1,350-case suite contains 450 development cases and a separately
frozen 900-case blind holdout, including 150 human-review records. Refused cases use only
`INSUFFICIENT_VERIFIED_SUPPORT`.

The support gate uses evidence from one configured retrieval pass. It answers only when
authorization, component completeness, exact claim support, applicability, quality, the
frozen support threshold, verification, and citation reconstruction all pass. It discloses
direct applicable conflicts and otherwise refuses neutrally. It does not identify the cause
of insufficient support or perform a subsequent document retrieval.

Results apply to this synthetic benchmark and fail-closed architecture; universal
correctness is not claimed.

## Consumed execution result

The blind holdout was executed once and must not be rerun. Its frozen category ordering
placed all answer and conflict cases in development and all 900 refusal cases in the blind
partition. Refusal safety passed 900/900 with zero visible claims, citations, scope leaks,
or post-insufficiency actions. Answer, citation, and conflict assurance are not measurable
from this consumed partition, so the overall result is **PARTIAL PASS** and no commit or
release claim is permitted.

## Grounding Assurance v2

V2 is independent of v1 and uses new deterministic seeds, case IDs, questions, evidence
spans, documents, and split assignments. Its 180 document families were shuffled and
assigned as 60 development families and 120 blind families before cases were generated;
no family, question, or exact evidence span crosses the split.

Preflight passed with 360 supported, 405 neutral-refusal, and 135 conflict blind cases.
Every required critical category has 23–24 cases and every metric denominator is non-zero.
The frozen threshold remained `0.72`. The blind checksum is
`4515b533b96cfc907aeb08721ff05df21654d211466116ad59c43638565f32aa` and the family-split
checksum is `ffca831b1d3fbf99eb72a4e0c26b8dffef87e26f8f33d4ae4e66f828b5048df8`.

V2 was executed exactly once. All 900 decisions matched: 360 answers, 405 refusals, and
135 conflicts. Claim/citation precision and recall, critical-fact accuracy, refusal and
conflict accuracy, injection resistance, provider fallback, and claim-to-evidence integrity
were 1.0000. Unsupported/unauthorized claims and citations, tenant/selected-scope leakage,
false conflicts, diagnosis leakage, adaptive attempts, post-insufficiency reformulations,
and Top-K changes were zero. The 150-case sheet is prepared for human review; no completed
human review is claimed.
