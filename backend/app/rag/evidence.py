from app.core.config import settings


def evidence_is_sufficient(scores: list[float], query: str, contents: list[str]) -> bool:
    if not scores or not contents:
        return False
    strong = max(scores) >= settings.evidence_min_score
    coverage = len(set(query.lower().split()) & set(" ".join(contents[:3]).lower().split())) / max(
        1, len(set(query.lower().split()))
    )
    return strong and coverage >= 0.2
