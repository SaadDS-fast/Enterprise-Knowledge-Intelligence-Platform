def weighted_fusion(
    lexical: list[float], semantic: list[float], lexical_weight: float = 0.45
) -> list[float]:
    if len(lexical) != len(semantic):
        raise ValueError("Score arrays must have equal length")
    semantic_weight = 1.0 - lexical_weight
    return [
        max(
            0.0,
            min(1.0, lexical_weight * lexical_score + semantic_weight * ((semantic_score + 1) / 2)),
        )
        for lexical_score, semantic_score in zip(lexical, semantic, strict=True)
    ]
