# Grounding assurance threat model

The protected invariant is that every visible claim has complete, authorized, applicable,
checksum-bound evidence from the original configured retrieval pass. Threats include tenant
or selected-document scope confusion, stale versions, numeric/entity/equation mutations,
incomplete composites, citation corruption, low-quality sources, prompt injection, and
provider outages.

The server owns the support decision. Models cannot authorize evidence, citations, or an
answer. Direct applicable conflicts are disclosed without selecting a winner. Every other
non-answer condition produces the same neutral refusal. No document instruction may trigger
tools, external calls, scope changes, internal-score disclosure, or another retrieval pass.

Grounding Assurance v2 additionally isolates related document versions and derivatives by
family before case generation. Preflight rejects family/question/evidence overlap, missing
decisions or checksums, duplicate IDs, zero decision denominators, or absent critical
categories before an execution counter can change.
