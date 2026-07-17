from app.rag.embeddings import tokenize


def rerank_score(query: str, content: str, base_score: float) -> float:
    query_tokens = set(tokenize(query))
    content_tokens = set(tokenize(content))
    overlap = len(query_tokens & content_tokens) / max(1, len(query_tokens))
    phrase_bonus = 0.08 if query.lower() in content.lower() else 0.0
    return max(0.0, min(1.0, 0.72 * base_score + 0.20 * overlap + phrase_bonus))
