from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from starlette.responses import HTMLResponse
from starlette.staticfiles import StaticFiles

from app.core.config import Settings

DOCS_CSP = (
    "default-src 'none'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "connect-src 'self'; "
    "img-src 'self'; "
    "font-src 'none'; "
    "frame-ancestors 'none'; "
    "base-uri 'none'; "
    "form-action 'none'"
)
SWAGGER_STATIC_DIR = Path(__file__).resolve().parents[1] / "static" / "swagger"


def register_docs(app: FastAPI, settings: Settings) -> None:
    if not settings.docs_url or not settings.openapi_url:
        return

    app.mount(
        "/static/swagger",
        StaticFiles(directory=SWAGGER_STATIC_DIR),
        name="swagger-static",
    )

    @app.get(settings.docs_url, include_in_schema=False)
    async def swagger_docs() -> HTMLResponse:
        html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{settings.app_name} - API docs</title>
  <link rel="stylesheet" href="/static/swagger/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="/static/swagger/swagger-ui-bundle.js"></script>
  <script src="/static/swagger/swagger-ui-init.js"></script>
</body>
</html>
"""
        return HTMLResponse(html, headers={"Content-Security-Policy": DOCS_CSP})
