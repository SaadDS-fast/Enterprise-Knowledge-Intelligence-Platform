def test_missing_authentication_is_rejected(client):
    response = client.get("/api/v1/documents")
    assert response.status_code == 401
