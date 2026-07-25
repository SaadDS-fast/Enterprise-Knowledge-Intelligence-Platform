from fastapi.testclient import TestClient

from app.api.docs import DOCS_CSP
from app.api.middleware.security_headers import STRICT_CSP
from app.core.config import Settings
from app.main import create_app


def test_openapi_json_returns_schema_when_docs_enabled(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["openapi"].startswith("3.")
    assert "/api/v1/search" in payload["paths"]


def test_docs_use_local_swagger_assets_and_no_cdn_urls(client):
    response = client.get("/docs")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert '<div id="swagger-ui">' in response.text
    assert "/static/swagger/swagger-ui.css" in response.text
    assert "/static/swagger/swagger-ui-bundle.js" in response.text
    assert "/static/swagger/swagger-ui-init.js" in response.text
    assert "cdn.jsdelivr.net" not in response.text
    assert "unpkg.com" not in response.text
    assert "https://" not in response.text


def test_local_swagger_assets_return_200(client):
    css = client.get("/static/swagger/swagger-ui.css")
    js = client.get("/static/swagger/swagger-ui-bundle.js")
    init = client.get("/static/swagger/swagger-ui-init.js")

    assert css.status_code == 200
    assert "text/css" in css.headers["content-type"]
    assert js.status_code == 200
    assert "javascript" in js.headers["content-type"]
    assert init.status_code == 200
    assert "javascript" in init.headers["content-type"]


def test_docs_csp_allows_only_same_origin_docs_requirements(client):
    response = client.get("/docs")

    assert response.headers["content-security-policy"] == DOCS_CSP
    assert "script-src 'self'" in DOCS_CSP
    assert "style-src 'self'" in DOCS_CSP
    assert "connect-src 'self'" in DOCS_CSP
    assert "unsafe-inline" not in DOCS_CSP
    assert "https:" not in DOCS_CSP
    assert "*" not in DOCS_CSP


def test_normal_api_responses_retain_strict_csp(client):
    response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.headers["content-security-policy"] == STRICT_CSP


def test_docs_and_openapi_are_disabled_in_production_mode():
    production_settings = Settings(
        _env_file=None,
        app_env="production",
        secret_key="production-secret-key-that-is-long-enough-123",  # noqa: S106
        database_url="sqlite+aiosqlite:///:memory:",
        cors_origins=["https://example.com"],
        trusted_hosts=["testserver"],
        metrics_enabled=False,
        otel_enabled=False,
    )
    production_app = create_app(production_settings)
    client = TestClient(production_app)

    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
