"""Evaluation worker pipeline adapter."""

from app.evaluation.runner import score_pairs


def evaluate_pairs(pairs: list[tuple[str, str]]) -> dict[str, float]:
    """Score predicted/reference answer pairs inside an evaluation worker."""
    return score_pairs(pairs)
