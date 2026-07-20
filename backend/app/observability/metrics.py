from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
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
INGESTION_SUBMITTED = Counter("ekip_ingestion_jobs_submitted_total", "Ingestion jobs submitted")
INGESTION_COMPLETED = Counter("ekip_ingestion_jobs_completed_total", "Ingestion jobs completed")
INGESTION_FAILED = Counter("ekip_ingestion_jobs_failed_total", "Ingestion jobs failed")


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
