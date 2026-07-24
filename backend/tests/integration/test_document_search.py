def isolated_headers(client, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Isolated Search User",
            "password": "correct-horse-battery-staple",
            "organization_name": f"Org {email}",
            "workspace_name": "General",
        },
    )
    assert response.status_code in {200, 201}, response.text
    payload = response.json()
    return {
        "Authorization": f"Bearer {payload['access_token']}",
        "X-Workspace-ID": payload["workspace_id"],
    }


def test_upload_ingest_and_search(client, auth_headers):
    content = (
        b"The Enterprise Knowledge Intelligence Platform uses hybrid retrieval. "
        b"It combines lexical BM25 evidence with semantic embeddings and abstains "
        b"when evidence is insufficient."
    )
    upload = client.post(
        "/api/v1/documents",
        headers=auth_headers,
        files={"file": ("architecture.txt", content, "text/plain")},
    )
    assert upload.status_code == 202, upload.text
    documents = client.get("/api/v1/documents", headers=auth_headers)
    assert documents.status_code == 200
    assert any(item["status"] == "ready" for item in documents.json())
    search = client.post(
        "/api/v1/search",
        headers=auth_headers,
        json={"query": "What retrieval method does the platform use?"},
    )
    assert search.status_code == 200, search.text
    payload = search.json()
    assert (
        payload["evidence"]
        and "hybrid" in (payload["answer"] + payload["evidence"][0]["content"]).lower()
    )


def test_unrelated_question_abstains(client, auth_headers):
    upload = client.post(
        "/api/v1/documents",
        headers=auth_headers,
        files={
            "file": (
                "atlas.txt",
                b"Project Atlas was launched in March 2025. The owner is Operations Analytics.",
                "text/plain",
            )
        },
    )
    assert upload.status_code == 202, upload.text
    search = client.post(
        "/api/v1/search",
        headers=auth_headers,
        json={"query": "What is the capital of the unrelated fictional country Virellia?"},
    )
    assert search.status_code == 200, search.text
    payload = search.json()
    assert payload["abstained"] is True
    assert payload["sufficient_evidence"] is False


def test_demo_topic_direct_heading_value_answer(client):
    headers = isolated_headers(client, "search-demo-topic@example.com")
    upload = client.post(
        "/api/v1/documents",
        headers=headers,
        files={
            "file": (
                "1st-year-maths-demo.txt",
                b"Topic: Functions\n\n"
                b"A function is a relation in which every input has exactly one output.\n\n"
                b"Tutor qualification: MS Data Science\n\n"
                b"Teaching method: Concept-first teaching",
                "text/plain",
            )
        },
    )
    assert upload.status_code == 202, upload.text

    search = client.post(
        "/api/v1/search",
        headers=headers,
        json={"query": "What is the demo topic?"},
    )

    assert search.status_code == 200, search.text
    payload = search.json()
    assert payload["abstained"] is False
    assert payload["outcome"] == "ANSWER_SUPPORTED"
    assert payload["support_status"] == "SUPPORTED"
    assert payload["answer"] == "The demo topic is Functions."
    assert payload["answer_value"] == "Functions"
    assert payload["citations"]
    assert payload["conflicts"] == []


def test_unrelated_heading_values_do_not_conflict(client):
    headers = isolated_headers(client, "search-non-conflict@example.com")
    response = client.post(
        "/api/v1/documents",
        headers=headers,
        files={
            "file": (
                "demo-non-conflict.txt",
                b"Demo topic: Functions\n\n"
                b"Tutor qualification: MS Data Science\n\n"
                b"Teaching method: Concept-first teaching",
                "text/plain",
            )
        },
    )
    assert response.status_code == 202, response.text

    search = client.post(
        "/api/v1/search",
        headers=headers,
        json={"query": "Demo topic?"},
    )

    assert search.status_code == 200, search.text
    payload = search.json()
    assert payload["abstained"] is False
    assert payload["answer_value"] == "Functions"
    assert payload["conflicts"] == []


def test_genuine_demo_topic_conflict_abstains(client):
    headers = isolated_headers(client, "search-conflict@example.com")
    for filename, content in (
        ("demo-topic-a.txt", b"Demo topic: Functions"),
        ("demo-topic-b.txt", b"Demo topic: Trigonometry"),
    ):
        response = client.post(
            "/api/v1/documents",
            headers=headers,
            files={"file": (filename, content, "text/plain")},
        )
        assert response.status_code == 202, response.text

    search = client.post(
        "/api/v1/search",
        headers=headers,
        json={"query": "What is the demo topic?"},
    )

    assert search.status_code == 200, search.text
    payload = search.json()
    assert payload["abstained"] is True
    assert payload["outcome"] == "CONFLICTING_EVIDENCE"
    assert payload["conflicts"]
    assert set(payload["conflicts"][0]["values"]) >= {"Functions", "Trigonometry"}


def test_evaluation_normalized_value_match(client):
    headers = isolated_headers(client, "search-evaluation@example.com")
    upload = client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("evaluation-demo.txt", b"Topic: Functions", "text/plain")},
    )
    assert upload.status_code == 202, upload.text

    evaluation = client.post(
        "/api/v1/evaluation",
        headers=headers,
        json={
            "name": "Demo topic quality check",
            "pipeline": "standard_search",
            "cases": [{"question": "What is the demo topic?", "expected_answer": "Functions"}],
        },
    )

    assert evaluation.status_code == 201, evaluation.text
    metrics = evaluation.json()["metrics_json"]
    assert metrics["pass_rate"] == 1
    assert metrics["normalized_answer_match"] == 1
    assert metrics["citation_validity"] == 1
