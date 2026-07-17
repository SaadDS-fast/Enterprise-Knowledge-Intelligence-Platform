def test_workspace_header_cannot_escape_membership(client, auth_headers):
    headers = dict(auth_headers)
    headers["X-Workspace-ID"] = "00000000-0000-0000-0000-000000000001"
    response = client.get("/api/v1/documents", headers=headers)
    assert response.status_code in {403, 404}
