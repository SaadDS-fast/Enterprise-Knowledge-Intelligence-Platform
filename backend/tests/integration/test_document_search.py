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
    metadata = payload["evidence"][0]["metadata"]
    assert metadata["embedding_version"] == "deterministic-hash-v1"
    assert metadata["embedding_dimension"] == 384
    assert metadata["indexing_version"] == "2.0"


def test_reindex_is_authorized_and_idempotent(client, auth_headers):
    upload = client.post(
        "/api/v1/documents",
        headers=auth_headers,
        files={"file": ("reindex.txt", b"Function: exactly one output per input.", "text/plain")},
    )
    assert upload.status_code == 202, upload.text
    document_id = upload.json()["document"]["id"]
    headers = {**auth_headers, "Idempotency-Key": "phase-2-reindex"}

    first = client.post(f"/api/v1/documents/{document_id}/reindex", headers=headers)
    replay = client.post(f"/api/v1/documents/{document_id}/reindex", headers=headers)

    assert first.status_code == 202, first.text
    assert replay.status_code == 202, replay.text
    assert first.json()["job_id"] == replay.json()["job_id"]
    assert replay.json()["idempotent"] is True


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


def test_selected_document_scope_excludes_unrelated_documents(client):
    headers = isolated_headers(client, "search-scope@example.com")
    target = client.post(
        "/api/v1/documents",
        headers=headers,
        files={
            "file": (
                "practice-topics.txt",
                b"Section: Functions\nQuestion 1: Determine whether the relation is a function.",
                "text/plain",
            )
        },
    )
    unrelated = client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("demo-topic.txt", b"Demo topic: Trigonometry", "text/plain")},
    )
    assert target.status_code == 202, target.text
    assert unrelated.status_code == 202, unrelated.text
    target_id = target.json()["document"]["id"]

    search = client.post(
        "/api/v1/search",
        headers=headers,
        json={
            "query": "What topics are covered by the practice questions?",
            "document_ids": [target_id],
        },
    )

    assert search.status_code == 200, search.text
    payload = search.json()
    assert payload["abstained"] is False
    assert payload["topic_items"][0]["label"] == "Functions"
    assert {item["document_id"] for item in payload["evidence"]} == {target_id}
    assert all(citation["document_id"] == target_id for citation in payload["citations"])
    assert payload["active_document_scope"] == [
        {"document_id": target_id, "title": "practice-topics"}
    ]


def test_unauthorized_document_scope_is_rejected(client):
    owner_headers = isolated_headers(client, "search-owner@example.com")
    other_headers = isolated_headers(client, "search-other@example.com")
    upload = client.post(
        "/api/v1/documents",
        headers=owner_headers,
        files={"file": ("private.txt", b"Topic: Functions", "text/plain")},
    )
    assert upload.status_code == 202, upload.text

    search = client.post(
        "/api/v1/search",
        headers=other_headers,
        json={
            "query": "What topics are covered?",
            "document_ids": [upload.json()["document"]["id"]],
        },
    )

    assert search.status_code == 404


def test_topic_list_multiple_headings_are_not_conflicts(client):
    headers = isolated_headers(client, "search-topic-list@example.com")
    upload = client.post(
        "/api/v1/documents",
        headers=headers,
        files={
            "file": (
                "as-practice-questions.txt",
                b"Section: Functions\n"
                b"Question 1: Determine whether the given relation is a function.\n\n"
                b"Section: Kinematics\n"
                b"Question 2: Given displacement as a function of time, calculate velocity.\n\n"
                b"Section: Elasticity\n"
                b"Question 3: Calculate the extension of a composite wire.",
                "text/plain",
            )
        },
    )
    assert upload.status_code == 202, upload.text

    search = client.post(
        "/api/v1/search",
        headers=headers,
        json={
            "query": "Which topics are these practice questions from?",
            "document_ids": [upload.json()["document"]["id"]],
        },
    )

    assert search.status_code == 200, search.text
    payload = search.json()
    assert payload["outcome"] == "ANSWER_SUPPORTED"
    assert payload["support_status"] == "SUPPORTED"
    assert payload["conflicts"] == []
    assert [item["label"] for item in payload["topic_items"]] == [
        "Functions",
        "Kinematics",
        "Elasticity",
    ]
    assert "The practice questions cover:" in payload["answer"]
    assert "vat timetis" not in payload["answer"]
    assert len(payload["citations"]) == 3


def test_topic_list_deduplicates_equivalent_labels(client):
    headers = isolated_headers(client, "search-topic-dedupe@example.com")
    upload = client.post(
        "/api/v1/documents",
        headers=headers,
        files={
            "file": (
                "duplicate-topics.txt",
                b"Section: Functions\nQuestion 1: Identify the domain.\n\n"
                b"Topic: Functions\nQuestion 2: Identify the range.",
                "text/plain",
            )
        },
    )
    assert upload.status_code == 202, upload.text

    search = client.post(
        "/api/v1/search",
        headers=headers,
        json={
            "query": "List the subjects covered by the questions.",
            "document_ids": [upload.json()["document"]["id"]],
        },
    )

    assert search.status_code == 200, search.text
    assert [item["label"] for item in search.json()["topic_items"]] == ["Functions"]


def test_low_confidence_topic_inference_abstains_without_raw_chunk_answer(client):
    headers = isolated_headers(client, "search-low-confidence-topics@example.com")
    upload = client.post(
        "/api/v1/documents",
        headers=headers,
        files={
            "file": (
                "unheaded-practice.txt",
                b"Question 1: Determine whether the given relation is a function.\n"
                b"Question 2: Given displacement s(t), calculate velocity.\n",
                "text/plain",
            )
        },
    )
    assert upload.status_code == 202, upload.text

    search = client.post(
        "/api/v1/search",
        headers=headers,
        json={
            "query": "What chapters do these questions belong to?",
            "document_ids": [upload.json()["document"]["id"]],
        },
    )

    assert search.status_code == 200, search.text
    payload = search.json()
    assert payload["abstained"] is True
    assert payload["outcome"] == "INSUFFICIENT_EVIDENCE"
    assert payload["topic_items"] == []
    assert "cannot be determined confidently" in payload["answer"]
    assert "Question 1:" not in payload["answer"]


def test_malformed_extracted_text_is_not_topic_label(client):
    headers = isolated_headers(client, "search-malformed-topic@example.com")
    upload = client.post(
        "/api/v1/documents",
        headers=headers,
        files={
            "file": (
                "malformed-practice.txt",
                b"Question 1: vat timetis given byv= 0.6t 2 -0.05t 3 calculate velocity.",
                "text/plain",
            )
        },
    )
    assert upload.status_code == 202, upload.text

    search = client.post(
        "/api/v1/search",
        headers=headers,
        json={
            "query": "What topics are covered by the practice questions?",
            "document_ids": [upload.json()["document"]["id"]],
        },
    )

    assert search.status_code == 200, search.text
    payload = search.json()
    assert payload["abstained"] is True
    assert payload["topic_items"] == []
    assert "vat timetis" not in payload["answer"]


def test_unique_document_name_in_query_scopes_search(client):
    headers = isolated_headers(client, "search-named-scope@example.com")
    target = client.post(
        "/api/v1/documents",
        headers=headers,
        files={
            "file": (
                "AS_Practice_questions.txt",
                b"Section: Functions\nQuestion 1: Test.",
                "text/plain",
            )
        },
    )
    client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("1st-year-maths-demo.txt", b"Demo topic: Trigonometry", "text/plain")},
    )
    assert target.status_code == 202, target.text

    search = client.post(
        "/api/v1/search",
        headers=headers,
        json={
            "query": (
                "In AS_Practice_questions, what topics are covered by the practice questions?"
            )
        },
    )

    assert search.status_code == 200, search.text
    payload = search.json()
    assert payload["active_document_scope"][0]["title"] == "AS_Practice_questions"
    assert {item["document_id"] for item in payload["evidence"]} == {
        target.json()["document"]["id"]
    }


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
    assert payload["citations"]
    assert any("Functions" in citation["excerpt"] for citation in payload["citations"])
    assert any("Trigonometry" in citation["excerpt"] for citation in payload["citations"])


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


def test_supported_quadratic_definition_has_equation_condition_and_citation(client):
    headers = isolated_headers(client, "equation-browser-closure@example.com")
    upload = client.post(
        "/api/v1/documents",
        headers=headers,
        files={
            "file": (
                "quadratic-equations.txt",
                b"Topic: Quadratic Equations\nDefinition:\n"
                b"A quadratic equation has the form ax\xc2\xb2 + bx + c = 0, "
                b"where a is not zero.",
                "text/plain",
            )
        },
    )
    assert upload.status_code == 202, upload.text
    document_id = upload.json()["document"]["id"]

    response = client.post(
        "/api/v1/search",
        headers=headers,
        json={"query": "What is a quadratic equation?", "document_ids": [document_id]},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["response_state"]["primary_state"] == "SUPPORTED", payload["response_state"][
        "diagnostics"
    ]
    assert "ax² + bx + c = 0" in payload["answer"]
    assert "a is not zero" in payload["answer"]
    assert payload["citations"][0]["document_id"] == document_id
    assert "ax² + bx + c = 0" in payload["citations"][0]["excerpt"]


def test_supported_negation_serializes_and_displays_claim_citation_data(client):
    headers = isolated_headers(client, "negation-browser-closure@example.com")
    upload = client.post(
        "/api/v1/documents",
        headers=headers,
        files={
            "file": (
                "travel-prohibition.txt",
                b"Employees must not exceed the approved travel limit.",
                "text/plain",
            )
        },
    )
    assert upload.status_code == 202, upload.text
    document_id = upload.json()["document"]["id"]

    response = client.post(
        "/api/v1/search",
        headers=headers,
        json={"query": "What is prohibited?", "document_ids": [document_id]},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["response_state"]["primary_state"] == "SUPPORTED"
    assert "must not exceed" in payload["answer"]
    assert len(payload["citations"]) == 1
    assert payload["citations"][0]["document_id"] == document_id
    assert "must not exceed" in payload["citations"][0]["excerpt"]
    assert payload["response_state"]["claims"][0]["citation_ids"]


def test_single_source_owner_effective_date_is_supported_composite(client):
    headers = isolated_headers(client, "owner-date-browser-closure@example.com")
    upload = client.post(
        "/api/v1/documents",
        headers=headers,
        files={
            "file": (
                "policy-details.txt",
                b"Policy Owner:\nThe policy owner is Ayesha Khan.\n"
                b"Effective Date:\nThe policy is effective from 1 February 2026.",
                "text/plain",
            )
        },
    )
    assert upload.status_code == 202, upload.text
    document_id = upload.json()["document"]["id"]

    response = client.post(
        "/api/v1/search",
        headers=headers,
        json={
            "query": "Who owns the policy and when does it become effective?",
            "document_ids": [document_id],
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["response_state"]["primary_state"] == "SUPPORTED_COMPOSITE"
    assert "Ayesha Khan" in payload["answer"]
    assert "1 February 2026" in payload["answer"]
    assert len(payload["response_state"]["claims"]) == 2
    assert all(claim["citation_ids"] for claim in payload["response_state"]["claims"])
    assert {citation["document_id"] for citation in payload["citations"]} == {document_id}
