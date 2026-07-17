from app.rag.embeddings import cosine_similarity, embed_text


def test_embeddings_are_deterministic_and_normalized():
    left = embed_text("enterprise knowledge platform")
    right = embed_text("enterprise knowledge platform")
    assert left == right and cosine_similarity(left, right) > 0.99
