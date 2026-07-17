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
