from app.evaluation.generation_metrics import exact_match, token_f1


def score_pairs(pairs: list[tuple[str, str]]) -> dict[str, float]:
    if not pairs:
        return {"exact_match": 0.0, "token_f1": 0.0}
    return {
        "exact_match": sum(exact_match(p, r) for p, r in pairs) / len(pairs),
        "token_f1": sum(token_f1(p, r) for p, r in pairs) / len(pairs),
    }
