def weighted_fusion(
    lexical: list[float],
    semantic: list[float],
    lexical_weight: float = 0.45,
    semantic_weight: float | None = None,
) -> list[float]:
    if len(lexical) != len(semantic):
        raise ValueError("Score arrays must have equal length")
    semantic_weight = 1.0 - lexical_weight if semantic_weight is None else semantic_weight
    if abs(lexical_weight + semantic_weight - 1.0) > 1e-6:
        raise ValueError("Fusion weights must sum to 1")
    return [
        max(
            0.0,
            min(1.0, lexical_weight * lexical_score + semantic_weight * ((semantic_score + 1) / 2)),
        )
        for lexical_score, semantic_score in zip(lexical, semantic, strict=True)
    ]
