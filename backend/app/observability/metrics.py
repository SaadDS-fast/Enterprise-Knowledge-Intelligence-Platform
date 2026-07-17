from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

REQUESTS = Counter("ekip_http_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram(
    "ekip_http_request_duration_seconds", "HTTP request latency", ["method", "path"]
)


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
