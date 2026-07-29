def test_liveness(client):
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_runtime_identity_exposes_only_safe_public_profile(client):
    response = client.get("/api/v1/health/runtime")

    assert response.status_code == 200
    payload = response.json()
    assert payload["application"] == "ekip-backend"
    assert payload["compatibility_id"]
    assert set(payload["features"]) == {
        "agentic_rag",
        "agentic_research",
        "external_apis",
        "semantic_embeddings",
        "reranker",
    }
    serialized = str(payload).lower()
    assert "secret" not in serialized
    assert "database" not in serialized
    assert "model_alias" not in serialized
