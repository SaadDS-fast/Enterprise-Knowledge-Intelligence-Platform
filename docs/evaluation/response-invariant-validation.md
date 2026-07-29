# Response invariant validation

Validation uses fresh deterministic fixtures and does not execute or modify consumed
blind retrieval benchmarks.

| Case | Deterministic result |
| --- | --- |
| Supported fact with focused citation | pass |
| Equivalent approval wording | no conflict |
| Equivalent PKR/unit wording | no conflict |
| Different allowance values | value conflict with two cited sides |
| Different approval roles | role conflict |
| Current versus superseded | current version resolves |
| Revenue versus budget | distinct attributes |
| Knowledge absence | no answer or answer citation |
| Retrieval unavailable | retrieval failure, not absence |
| Ambiguous query with high confidence | rejected |
| Complete composite | multiple individually cited claims |
| Incomplete composite | rejected and failed closed |
| Low-quality source | low-quality/insufficient state |
| Selected-document citation escape | rejected and failed closed |
| Tenant/workspace isolation | authorization regressions pass |
| Semantic plus lexical-only fallback | rejected and failed closed |
| Cancelled supported answer | rejected and failed closed |

The table-driven suite is `tests/unit/test_response_state_consistency.py`.
Existing integration and security tests cover JWT authentication,
tenant/workspace isolation, selected-document authorization, document IDOR, prompt
injection, SSRF, parser validation, CSP, safe runtime identity, and local-model
allowlisting.

New clients use `primary_state`, `evidence_decision`, `conflict`, `confidence`,
`retrieval`, `scope`, `claims`, `citation_ids`, and `user_message`. Legacy API fields
remain a derived compatibility view.

Next phase: locally operated Ollama grounded generation may be added only after this
contract remains the mandatory final gate. No generative provider is in this phase.
