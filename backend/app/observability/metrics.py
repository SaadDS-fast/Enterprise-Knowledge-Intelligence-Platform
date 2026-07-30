from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.responses import Response

REQUESTS = Counter("ekip_http_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram(
    "ekip_http_request_duration_seconds", "HTTP request latency", ["method", "path"]
)
RETRIEVAL_RETRIES = Counter("ekip_retrieval_retries_total", "Retrieval retry attempts")
RETRIEVAL_RECOVERIES = Counter(
    "ekip_retrieval_recoveries_total", "Retrieval retries that recovered sufficient evidence"
)
KNOWLEDGE_ABSENCE = Counter(
    "ekip_knowledge_absence_total", "Searches classified as knowledge absent"
)
PARTIAL_EVIDENCE = Counter("ekip_partial_evidence_total", "Searches with partial evidence")
ABSTENTIONS = Counter("ekip_abstentions_total", "Searches that abstained")
RETRIEVAL_LATENCY = Histogram("ekip_retrieval_duration_seconds", "Retrieval duration")
DIAGNOSIS_LATENCY = Histogram("ekip_diagnosis_duration_seconds", "Evidence diagnosis duration")
GENERATION_REQUESTS = Counter(
    "ekip_generation_requests_total", "Grounded generation requests", ["provider"]
)
GENERATION_SUCCESSES = Counter(
    "ekip_generation_successes_total", "Verified grounded generations", ["provider"]
)
GENERATION_VERIFICATION_FAILURES = Counter(
    "ekip_generation_verification_failures_total",
    "Grounded generation verification failures",
    ["category"],
)
GENERATION_FALLBACKS = Counter(
    "ekip_generation_fallbacks_total", "Safe generation fallbacks", ["category"]
)
GENERATION_TIMEOUTS = Counter(
    "ekip_generation_timeouts_total", "Grounded generation timeouts", ["provider"]
)
GENERATION_DURATION = Histogram(
    "ekip_generation_duration_seconds", "Grounded generation duration", ["provider", "outcome"]
)
INGESTION_SUBMITTED = Counter("ekip_ingestion_jobs_submitted_total", "Ingestion jobs submitted")
INGESTION_COMPLETED = Counter("ekip_ingestion_jobs_completed_total", "Ingestion jobs completed")
INGESTION_FAILED = Counter("ekip_ingestion_jobs_failed_total", "Ingestion jobs failed")
WORKER_TASKS_RECEIVED = Counter(
    "ekip_worker_tasks_received_total", "Celery tasks received by worker role", ["worker_role"]
)
WORKER_TASKS_COMPLETED = Counter(
    "ekip_worker_tasks_completed_total", "Celery tasks completed by worker role", ["worker_role"]
)
WORKER_TASKS_FAILED = Counter(
    "ekip_worker_tasks_failed_total", "Celery tasks failed by worker role", ["worker_role"]
)
WORKER_TASKS_RETRIED = Counter(
    "ekip_worker_tasks_retried_total", "Celery tasks retried by worker role", ["worker_role"]
)
WORKER_TASK_DURATION = Histogram(
    "ekip_worker_task_duration_seconds", "Celery task duration by worker role", ["worker_role"]
)
WORKER_QUEUE_DELAY = Histogram(
    "ekip_worker_queue_delay_seconds", "Celery task queue delay by worker role", ["worker_role"]
)
WORKER_ACTIVE_TASKS = Gauge(
    "ekip_worker_active_tasks", "Currently active Celery tasks by worker role", ["worker_role"]
)
AGENT_RUNS_STARTED = Counter("ekip_agent_runs_started_total", "Agent runs started")
AGENT_RUNS_COMPLETED = Counter("ekip_agent_runs_completed_total", "Agent runs completed")
AGENT_RUNS_FAILED = Counter("ekip_agent_runs_failed_total", "Agent runs failed")
AGENT_TOOL_CALLS = Counter("ekip_agent_tool_calls_total", "Agent tool calls", ["tool"])
AGENT_REPLANS = Counter("ekip_agent_replans_total", "Agent replans")
AGENT_FALLBACKS = Counter("ekip_agent_fallbacks_total", "Agent fallbacks")
AGENT_DURATION = Histogram("ekip_agent_duration_seconds", "Agent run duration")
AGENT_TOOL_DURATION = Histogram("ekip_agent_tool_duration_seconds", "Agent tool duration", ["tool"])
AGENT_EXTERNAL_TOOL_CALLS = Counter(
    "ekip_agent_external_tool_calls_total",
    "Agent external tool calls",
    ["provider", "tool", "outcome"],
)
AGENT_EXTERNAL_TOOL_FAILURES = Counter(
    "ekip_agent_external_tool_failures_total",
    "Agent external tool failures",
    ["provider", "tool", "outcome"],
)
AGENT_EXTERNAL_TOOL_DURATION = Histogram(
    "ekip_agent_external_tool_duration_seconds",
    "Agent external tool duration",
    ["provider", "tool", "outcome"],
)
AGENT_EXTERNAL_SOURCES_USED = Counter(
    "ekip_agent_external_sources_used_total",
    "Agent external sources used",
    ["provider", "tool"],
)
AGENT_SSRF_BLOCKS = Counter(
    "ekip_agent_ssrf_blocks_total", "Agent outbound SSRF blocks", ["provider", "outcome"]
)
AGENT_EXTERNAL_TIMEOUTS = Counter(
    "ekip_agent_external_timeouts_total",
    "Agent external tool timeouts",
    ["provider", "tool"],
)
AGENT_EVIDENCE_ITEMS = Counter(
    "ekip_agent_evidence_items_total",
    "Agent evidence items normalized",
    ["source_type"],
)
AGENT_EVIDENCE_DEDUPLICATED = Counter(
    "ekip_agent_evidence_deduplicated_total",
    "Agent evidence duplicates merged",
    ["source_type"],
)
AGENT_CLAIMS_VERIFIED = Counter(
    "ekip_agent_claims_verified_total",
    "Agent claims verified",
    ["verification_status"],
)
AGENT_CLAIMS_UNSUPPORTED = Counter(
    "ekip_agent_claims_unsupported_total",
    "Agent unsupported claims",
    ["outcome"],
)
AGENT_CONFLICTS_DETECTED = Counter(
    "ekip_agent_conflicts_detected_total",
    "Agent evidence conflicts detected",
    ["outcome"],
)
AGENT_CITATIONS_VALIDATED = Counter(
    "ekip_agent_citations_validated_total",
    "Agent citations validated",
    ["source_type", "outcome"],
)
AGENT_CITATIONS_REJECTED = Counter(
    "ekip_agent_citations_rejected_total",
    "Agent citations rejected",
    ["outcome"],
)
AGENT_SYNTHESIS_FALLBACKS = Counter(
    "ekip_agent_synthesis_fallbacks_total",
    "Agent deterministic synthesis fallbacks",
    ["outcome"],
)
AGENT_CONTEXT_BUDGET_TRUNCATIONS = Counter(
    "ekip_agent_context_budget_truncations_total",
    "Agent context budget truncations",
    ["outcome"],
)
AGENT_RESEARCH_JOBS_STARTED = Counter(
    "ekip_agent_research_jobs_started_total", "Agent research jobs started"
)
AGENT_RESEARCH_JOBS_COMPLETED = Counter(
    "ekip_agent_research_jobs_completed_total", "Agent research jobs completed"
)
AGENT_RESEARCH_JOBS_FAILED = Counter(
    "ekip_agent_research_jobs_failed_total", "Agent research jobs failed"
)
AGENT_RESEARCH_JOBS_CANCELLED = Counter(
    "ekip_agent_research_jobs_cancelled_total", "Agent research jobs cancelled"
)
AGENT_RESEARCH_STAGE_DURATION = Histogram(
    "ekip_agent_research_stage_duration_seconds",
    "Agent research stage duration",
    ["stage", "outcome"],
)
AGENT_RESEARCH_TOTAL_DURATION = Histogram(
    "ekip_agent_research_total_duration_seconds", "Agent research total duration"
)
AGENT_RESEARCH_SOURCES_USED = Counter(
    "ekip_agent_research_sources_used_total",
    "Agent research sources used",
    ["source_type"],
)
AGENT_RESEARCH_CLAIMS_VERIFIED = Counter(
    "ekip_agent_research_claims_verified_total",
    "Agent research claims verified",
    ["outcome"],
)
AGENT_RESEARCH_CITATIONS_VALIDATED = Counter(
    "ekip_agent_research_citations_validated_total",
    "Agent research citations validated",
    ["outcome"],
)
AGENT_RESEARCH_EXPORTS = Counter(
    "ekip_agent_research_exports_total",
    "Agent research exports",
    ["format", "outcome"],
)
AGENT_RESEARCH_EXPORT_FAILURES = Counter(
    "ekip_agent_research_export_failures_total",
    "Agent research export failures",
    ["format", "outcome"],
)
AGENT_RESEARCH_RETRIES = Counter(
    "ekip_agent_research_retries_total", "Agent research task retries", ["outcome"]
)


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
