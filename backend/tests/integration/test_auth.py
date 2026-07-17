def test_register_login_and_me(client):
    email = "new-user@example.com"
    password = "correct-horse-battery-staple"
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "New User",
            "password": password,
            "organization_name": "New Org",
            "workspace_name": "General",
        },
    )
    assert registered.status_code == 201
    token = registered.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["email"] == email
