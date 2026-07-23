from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from app.core.config import settings


def configure_tracing(app) -> None:
    if not settings.otel_enabled:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider(
            resource=Resource.create({"service.name": settings.otel_service_name})
        )
        provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(
                    endpoint=settings.otel_exporter_otlp_endpoint,
                    insecure=not settings.otel_exporter_otlp_endpoint.startswith("https"),
                )
            )
        )
        trace.set_tracer_provider(provider)
    except Exception:
        return


@contextmanager
def safe_span(name: str, **attributes: Any) -> Iterator[None]:
    if not settings.otel_enabled:
        yield
        return
    try:
        from opentelemetry import trace

        tracer = trace.get_tracer("ekip")
        safe_attributes = {
            key: value
            for key, value in attributes.items()
            if isinstance(value, str | int | float | bool) and value is not None
        }
        with tracer.start_as_current_span(name) as span:
            for key, value in safe_attributes.items():
                span.set_attribute(key, value)
            yield
    except Exception:
        yield
