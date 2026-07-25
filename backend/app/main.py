from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.docs import register_docs
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


def create_app(app_settings=settings) -> FastAPI:
    application = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        debug=app_settings.debug,
        docs_url=None,
        redoc_url=None,
        openapi_url=app_settings.openapi_url,
        lifespan=lifespan,
    )
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=app_settings.trusted_hosts)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=app_settings.cors_allow_credentials,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            app_settings.tenant_header,
            app_settings.request_id_header,
        ],
    )
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(RequestLoggingMiddleware)
    application.add_middleware(RequestSizeLimitMiddleware)
    application.add_middleware(RequestIDMiddleware)
    register_exception_handlers(application)
    application.include_router(api_router, prefix=app_settings.api_v1_prefix)
    register_docs(application, app_settings)
    if app_settings.metrics_enabled:
        application.add_api_route(
            "/metrics", metrics_response, methods=["GET"], include_in_schema=False
        )
    configure_tracing(application)
    return application


app = create_app()


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": settings.docs_url or "disabled",
    }
