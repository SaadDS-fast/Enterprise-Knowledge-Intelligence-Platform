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


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
