def test_mime_mismatch_is_rejected(client, auth_headers):
    response = client.post(
        "/api/v1/documents",
        headers=auth_headers,
        files={"file": ("fake.pdf", b"not a pdf", "application/pdf")},
    )
    assert response.status_code == 415


def test_text_file_with_pdf_mime_is_rejected(client, auth_headers):
    response = client.post(
        "/api/v1/documents",
        headers=auth_headers,
        files={"file": ("notes.txt", b"plain text content", "application/pdf")},
    )
    assert response.status_code == 415


def test_path_traversal_filename_is_sanitized(client, auth_headers):
    response = client.post(
        "/api/v1/documents",
        headers=auth_headers,
        files={"file": ("../../notes.txt", b"safe content for indexing", "text/plain")},
    )
    assert response.status_code == 202
