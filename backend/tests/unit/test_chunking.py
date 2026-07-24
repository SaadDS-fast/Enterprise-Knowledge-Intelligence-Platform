from app.rag.chunking import chunk_text


def test_chunking_respects_size():
    chunks = chunk_text("One sentence. " * 100, chunk_size=120, overlap=20)
    assert len(chunks) > 1 and all(len(chunk) <= 140 for chunk in chunks)


def test_chunking_preserves_heading_value_pairs():
    chunks = chunk_text(
        "\n".join(
            [
                "Topic: Functions",
                "Tutor qualification: MS Data Science",
                "Teaching method: Concept-first teaching",
            ]
        ),
        chunk_size=200,
        overlap=20,
    )

    assert "Topic: Functions" in chunks
    assert any(chunk == "Tutor qualification: MS Data Science" for chunk in chunks)
    assert not any(
        "Topic: Functions" in chunk and "Tutor qualification" in chunk for chunk in chunks
    )
