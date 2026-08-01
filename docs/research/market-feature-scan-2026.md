# Enterprise feature market scan (2026)

Status: research record

As-of and access date for all external sources: **2026-08-01**

Baseline: `3bcc571ed8aa19a01bbb2df7e1cdab51f4ef7651` (`v0.3.0-enterprise-rc2`)

## Scope and claim discipline

This is a time-bounded review of public, official documentation, not an exhaustive product
audit. “Not found” means only that the capability was not located in the cited pages reviewed;
it does not establish that a vendor lacks the capability privately, elsewhere, or in a later
release. Product terms and availability can change. No trial tenants or vendor APIs were tested.

The scan excludes any feature that diagnoses inadequate retrieval or absent knowledge, changes
retrieval after weak support, or explains a refusal technically. The existing terminal behavior
remains a neutral “insufficient verified support” refusal.

## Repository capability inventory

Classification is based on executable paths, tests, migrations, and operational documentation in
this repository—not on the product comparison below.

| Capability | Classification | Repository evidence / qualification |
|---|---|---|
| Ingestion | Production implemented | `backend/app/ingestion/pipeline.py`, upload service, jobs, tests |
| Parsing / structured extraction | Production implemented | `backend/app/ingestion/extractors.py`, extraction and ingestion tests |
| Chunking | Production implemented | Versioned ingestion pipeline and chunk persistence |
| Lexical retrieval | Production implemented | `backend/app/rag/bm25.py`, search service and tests |
| Semantic retrieval | Feature-flagged | Local/deterministic providers and hybrid retriever exist; configuration can disable it |
| Reranking | Feature-flagged | Allowlisted providers and deterministic fallback; configuration controls activation |
| Support gating | Production implemented | Static fail-closed support policy in grounded answer path |
| Conflict handling | Production implemented | Response-state/concept constraints and conflict test coverage |
| Refusal | Production implemented | Neutral insufficient-support response is enforced and validated |
| Citations | Production implemented | Evidence packets, authorized citation mapping, API serialization and tests |
| Answer planning | Production implemented | `backend/app/llm/answer_plan.py` and unit tests |
| Critical-fact locking | Production implemented | Immutable fact registry and drift rejection tests |
| Generation | Production implemented | Verified local/Ollama path plus extractive fallback; hosted providers are configured options |
| Controlled Agent | Feature-flagged | Orchestrator, bounded tool registry, policy checks, persistence and tests |
| Evaluation | Production implemented | Evaluation services/routes and committed development/consumed result artifacts |
| Research | Feature-flagged | Research service/API and explicit disabled-state integration test |
| Audit | Production implemented | Audit-event model/repository, search and agent event recording |
| Observability | Production implemented | Health/readiness, metrics/logging hooks and deployment runbooks |
| Multi-tenancy | Production implemented | Tenant/workspace scoping, authorization, storage keys and isolation tests |
| Document versions | Production implemented | `DocumentVersion`, current-version retrieval and version metadata |
| Backup / restore | Documented only | Operational procedures exist; no application-level backup engine is claimed |
| Deployment | Production implemented | Container/local production assets and AWS staging assets exist; AWS was not touched |
| Grounding Assurance v2 | Validated only | Frozen corpus/cases/results demonstrate the supplied assurance claims; it is not a runtime feature |

“Production implemented” here means present in the production application path; it does not mean
independently certified or deployed by this research task.

## Official-product scan

| Product | Publicly documented capabilities in reviewed sources | Capability not found in reviewed documentation / limitation |
|---|---|---|
| Microsoft 365 Copilot | Honors Microsoft 365 permissions and sensitivity labels; audit records can include prompts, responses, and referenced content, with referenced versions retained for investigation ([architecture, data protection, and auditing](https://learn.microsoft.com/en-us/microsoft-365/copilot/microsoft-365-copilot-architecture-data-protection-auditing)). | No portable, customer-verifiable signed answer certificate or default-offline verifier was found. “Referenced versions” is not evidence of cryptographic answer verification. |
| Amazon Q Business | Web answers show citations, snippets, source lists, and conversation history ([web experience](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/using-web-experience.html)); source attribution exposes document/index identifiers and snippets ([API](https://docs.aws.amazon.com/amazonq/latest/api-reference/API_SourceAttribution.html)); connectors index ACL/identity information used to filter responses ([connector concepts](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/connector-concepts.html)). | No signed portable answer, offline verification, or document-change impact analysis for earlier answers was found. |
| Google Gemini Enterprise | Search summaries provide citations and reference metadata, with an explicit warning that citations can be missing or misattributed ([search summaries](https://docs.cloud.google.com/gemini/enterprise/docs/get-search-summaries)); source ACLs and app IAM constrain access ([identity and ACLs](https://docs.cloud.google.com/gemini/enterprise/docs/identity), [app IAM](https://docs.cloud.google.com/gemini/enterprise/docs/iam-policy-for-apps)); Cloud Audit Logs cover service methods including answer queries ([audit logging](https://docs.cloud.google.com/gemini/enterprise/docs/audit-logging)). | No portable signed answer passport, offline replay, or evidence-span tamper check was found. |
| Glean | AI Answers documents references/citations, permission awareness and consistent results ([AI Answers](https://docs.glean.com/user-guide/assistant/ai-answers)); enterprise search describes real-time indexing and source-permission enforcement ([Glean Search](https://www.glean.com/enterprise-search)). | No answer-level detached signature, offline evidence verification, or prior-answer change-impact workflow was found. “Deterministic responses” is a vendor statement, not an independently tested guarantee here. |
| Elastic | Elasticsearch provides field/document-level security and documents its limitations ([access control](https://www.elastic.co/guide/en/elasticsearch/reference/8.19/field-and-document-access-control.html), [security limitations](https://www.elastic.co/guide/en/elasticsearch/reference/current/security-limitations.html)); Elastic describes RBAC, AI activity logging, audit and token tracking for its security AI offering ([AI for Security](https://www.elastic.co/security/ai/)). | The reviewed pages did not document a general-purpose signed answer artifact or offline answer/evidence verification. The security assistant is a narrower SOC comparison. |
| Coveo | RGA generates cited answers over permission-filtered enterprise content ([RGA overview](https://docs.coveo.com/en/n9de0370/)); its security page documents secure retrieval, grounding, zero retention and logged analytics ([RGA data security](https://docs.coveo.com/en/nbpd4153)); interaction telemetry includes citation clicks ([Headless RGA](https://docs.coveo.com/en/headless/latest/reference/documents/usage/relevance-generative-answering.html)). | No detached answer signature, portable offline verification bundle, or cryptographic evidence-span validation was found. |
| ServiceNow AI Search / Now Assist | AI Search documents highlighting, ML relevance, result cards and result controls ([AI Search results](https://www.servicenow.com/docs/r/platform-administration/ai-search/explore-features-results-ais.html)); Now Assist answer cards link to source records/documents and warn that generated output can be inaccurate ([Now Assist in AI Search](https://www.servicenow.com/docs/r/xanadu/platform-administration/ai-search/now-assist-ais.html)). | No answer passport, cryptographic verification, offline replay, or historical-answer impact analysis was found. |
| IBM watsonx Assistant / Orchestrate | Conversational search documents inline citations and confidence/citation metrics ([search analytics](https://cloud.ibm.com/docs/watson-assistant?topic=watson-assistant-conversational-search-analytics)); assistant analytics includes citation counts and response/retrieval confidence ([analytics](https://www.ibm.com/docs/en/watsonx/watson-orchestrate/base?topic=assistants-use-analytics-review-your-entire-assistant-glance)). | No portable signed answer or offline evidence-snapshot verifier was found. Confidence telemetry is not cryptographic integrity. |
| Salesforce Agentforce | Embedded citations expose source links ([citations release note](https://help.salesforce.com/s/articleView?id=release-notes.rn_citations.htm&language=en_US&release=256&type=5)); the Trust Layer documents access controls, grounding, guardrails, and prompt/response/trust-signal logging ([Trust and Agentforce](https://help.salesforce.com/s/articleView?id=ai.copilot_trust.htm&language=en_US&type=5)). | No detached answer signature, customer-portable verifier, or offline evidence validation was found. |
| Azure AI Document Intelligence | Returns word/field/region/signature extraction confidence and recommends human review for critical uses ([accuracy and confidence](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept/accuracy-confidence?view=doc-intel-4.0.0)). | This is document extraction rather than an enterprise answer system. No answer certificate or answer replay was found. |
| Google Cloud Document AI | Its document interchange model includes entity confidence, page anchors, revision provenance and human-review state ([Document API](https://docs.cloud.google.com/document-ai/docs/reference/rest/v1/Document)); evaluation exposes confidence thresholds and precision/recall tradeoffs ([evaluation](https://docs.cloud.google.com/document-ai/docs/evaluate)). | Provenance concerns extraction revisions, not a signed grounded-answer artifact; no offline answer verification was found. |
| IBM watsonx.governance | Documents governance workflows for AI use cases, risks, metrics, alerts and compliance management ([governance console](https://www.ibm.com/docs/en/watsonx/saas?topic=ai-managing-risk-compliance-governance-console)). | No claim-to-span signed answer passport or offline replay was found in the reviewed overview. |

### Cross-market pattern

Commonly documented: source links/citations, permission-aware access, grounded generation, feedback
or analytics, and platform audit records. Less commonly documented in this sample: portable
answer-level integrity artifacts, independent offline verification against an authorized snapshot,
and a clear separation between signature validity and current evidence freshness. This supports a
**differentiated combination** claim only.

## Recent primary-research scan (2024–2026)

| Work | Contribution and repository overlap | Productization evidence | Thesis risk | Complexity |
|---|---|---|---|---|
| [RAGAs: Automated Evaluation of Retrieval Augmented Generation](https://aclanthology.org/2024.eacl-demo.16/) (2024) | Reference-free metrics for context relevance, faithfulness and answer relevance; overlaps Evaluation. | Open-source framework; no signed-answer product claim assessed. | High if converted into failure diagnosis; retain only as evaluation context. | Medium |
| [ARES](https://aclanthology.org/2024.naacl-long.20/) (2024) | Synthetic training plus lightweight judges and prediction-powered inference for RAG evaluation; overlaps Evaluation. | Research implementation; no reviewed evidence of passport productization. | Medium; offline aggregate evaluation is safe, runtime diagnosis is excluded. | High |
| [RAGChecker](https://arxiv.org/abs/2408.08067) (2024) | Fine-grained retriever/generator diagnostic metrics; overlaps assurance measurement. | Public code from Amazon Science; not evidence that Amazon Q ships it. | **High/direct** because diagnosis is thesis-reserved; do not adopt. | High |
| [MIRAGE: Model Internals-based Answer Attribution](https://aclanthology.org/2024.emnlp-main.347/) (2024) | Attributes answer tokens to retrieved documents using model internals; adjacent to claim/citation verification. | Public code; no commercial productization established by reviewed evidence. | Low for post-answer attribution, but model-internal coupling raises feasibility. | High |
| [Towards Fine-Grained Citation Evaluation](https://aclanthology.org/2024.inlg-main.35/) (2024) | Compares citation-faithfulness metrics; supports careful separation of citation presence and faithfulness. | No commercial productization established. | Low if used only for offline evaluation. | Medium |
| [Ground Every Sentence / ReClaim](https://aclanthology.org/2025.findings-naacl.55/) (2025) | Interleaves references and claims for sentence-level attribution; overlaps existing claim-level citation mapping. | No commercial productization established in the reviewed primary source. | Medium: generation changes are out of scope; passport can consume existing mappings only. | High |
| [VISA: Visual Source Attribution](https://aclanthology.org/2025.acl-long.1456/) (2025) | Adds visual source attribution for multimodal RAG; relevant to span/page provenance. | No commercial productization established. | Low if the passport records existing page anchors; multimodal retrieval changes are excluded. | High |
| [Evaluation of Attribution Bias in Generator-Aware Retrieval](https://aclanthology.org/2025.findings-acl.1087/) (2025) | Studies bias introduced when retrieval is optimized for a generator; cautions against treating attribution as neutral. | No commercial productization established. | High for retriever adaptation; safe only as a limitation. | High |
| [AIP: Subverting RAG via Adversarial Instructional Prompt](https://aclanthology.org/2025.emnlp-main.801/) (2025) | Studies adversarial instructions in retrieved content; motivates immutable evidence hashes and adversarial tests. | No productization established. | Low: security validation does not diagnose ordinary retrieval failure. | Medium |

Research directly addressing signed, portable answer certificates and default-offline
verification was not found in this bounded primary-source set. That is a literature limitation,
not a novelty proof. Temporal/version-aware retrieval and counterfactual QA were screened as
adjacent topics but intentionally not converted into candidates that alter retrieval.

## Recommended direction

Proceed to specification—not implementation—of **Verifiable Answer Passport and Offline Audit
Replay**. It packages an already-supported answer, normalized claims, exact evidence identifiers,
version/checksum metadata and configuration fingerprints into a canonical, signed artifact. It
does not decide whether evidence is adequate and cannot initiate retrieval.

Defensible wording:

> A differentiated combination of verified grounding, portable signed answer evidence, and
> deterministic offline verification; these capabilities were not commonly documented together
> in the official enterprise-assistant pages reviewed as of 2026-08-01.

Do not claim world-first status, universal truth, or absolute tamper-proofing.

## Sources and reproducibility note

Every market statement above links to an official vendor page and every research statement links
to a primary paper record. Results are reproducible as a documentation review only; feature
availability, licensing, regional status, and undocumented behavior require vendor confirmation.
No external service, model, application tenant, or consumed benchmark was executed.
