import os
import shutil
from pathlib import Path

os.environ.update(
    {
        "APP_ENV": "testing",
        "DATABASE_URL": "sqlite+aiosqlite:////tmp/ekip_test.db",
        "AUTO_INIT_DB": "false",
        "SECRET_KEY": "testing-secret-key-that-is-long-enough-123456",
        "OBJECT_STORAGE_PROVIDER": "local",
        "LOCAL_STORAGE_PATH": "/tmp/ekip_test_storage",
        "OTEL_ENABLED": "false",
        "METRICS_ENABLED": "false",
        "REQUIRE_MALWARE_SCAN": "false",
        "TRUSTED_HOSTS": "testserver,localhost,127.0.0.1",
    }
)
import pytest
from fastapi.testclient import TestClient

from app.db.session import close_database, init_database
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def database():
    import asyncio

    Path("/tmp/ekip_test.db").unlink(missing_ok=True)
    shutil.rmtree("/tmp/ekip_test_storage", ignore_errors=True)
    asyncio.run(init_database())
    yield
    asyncio.run(close_database())
    Path("/tmp/ekip_test.db").unlink(missing_ok=True)
    shutil.rmtree("/tmp/ekip_test_storage", ignore_errors=True)


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def auth_headers(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "engineer@example.com",
            "full_name": "AI Engineer",
            "password": "correct-horse-battery-staple",
            "organization_name": "Example",
            "workspace_name": "General",
        },
    )
    if response.status_code == 409:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "engineer@example.com", "password": "correct-horse-battery-staple"},
        )
    payload = response.json()
    return {
        "Authorization": f"Bearer {payload['access_token']}",
        "X-Workspace-ID": payload["workspace_id"],
    }
