from app.core.config import settings

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "did",
    "does",
    "in",
    "is",
    "it",
    "its",
    "of",
    "the",
    "to",
    "was",
    "what",
    "when",
    "which",
    "who",
}


def key_terms(text: str) -> set[str]:
    return {
        token.strip(".,:;!?()[]{}\"'").lower()
        for token in text.split()
        if len(token.strip(".,:;!?()[]{}\"'")) >= 3
        and token.strip(".,:;!?()[]{}\"'").lower() not in STOPWORDS
    }


def evidence_is_sufficient(scores: list[float], query: str, contents: list[str]) -> bool:
    if not scores or not contents:
        return False
    strong = max(scores) >= settings.evidence_min_score
    query_terms = key_terms(query)
    if not query_terms:
        return strong
    evidence_terms = key_terms(" ".join(contents[:3]))
    coverage = len(query_terms & evidence_terms) / len(query_terms)
    return strong and coverage >= 0.34
