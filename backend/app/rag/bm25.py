from rank_bm25 import BM25Okapi

from app.rag.embeddings import tokenize


def bm25_scores(query: str, documents: list[str]) -> list[float]:
    if not documents:
        return []
    corpus = [tokenize(doc) for doc in documents]
    if not any(corpus):
        return [0.0] * len(documents)
    raw = list(BM25Okapi(corpus).get_scores(tokenize(query)))
    low, high = min(raw), max(raw)
    if high <= low:
        return [1.0 if value > 0 else 0.0 for value in raw]
    return [(value - low) / (high - low) for value in raw]
