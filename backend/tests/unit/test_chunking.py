from app.rag.chunking import chunk_text


def test_chunking_respects_size():
    chunks = chunk_text("One sentence. " * 100, chunk_size=120, overlap=20)
    assert len(chunks) > 1 and all(len(chunk) <= 140 for chunk in chunks)
