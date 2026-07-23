from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.middleware.logging import RequestLoggingMiddleware
from app.api.middleware.request_id import RequestIDMiddleware
from app.api.middleware.request_size import RequestSizeLimitMiddleware
from app.api.middleware.security_headers import SecurityHeadersMiddleware
from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import close_database, init_database
from app.exceptions.handlers import register_exception_handlers
from app.jobs.dispatcher import dispatch_pending_ingestion_jobs_loop
from app.observability.logging import configure_logging
from app.observability.metrics import metrics_response
from app.observability.tracing import configure_tracing

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_init_db:
        await init_database()
    dispatcher_task = asyncio.create_task(dispatch_pending_ingestion_jobs_loop())
    yield
    dispatcher_task.cancel()
    with suppress(asyncio.CancelledError):
        await dispatcher_task
    await close_database()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    docs_url=settings.docs_url,
    redoc_url=settings.redoc_url,
    lifespan=lifespan,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        settings.tenant_header,
        settings.request_id_header,
    ],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(RequestIDMiddleware)
register_exception_handlers(app)
app.include_router(api_router, prefix=settings.api_v1_prefix)
if settings.metrics_enabled:
    app.add_api_route("/metrics", metrics_response, methods=["GET"], include_in_schema=False)
configure_tracing(app)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": settings.docs_url or "disabled",
    }
