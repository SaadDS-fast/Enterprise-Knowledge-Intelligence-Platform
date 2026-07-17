def test_openapi_contains_core_routes(client):
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/documents" in paths
    assert "/api/v1/search" in paths
