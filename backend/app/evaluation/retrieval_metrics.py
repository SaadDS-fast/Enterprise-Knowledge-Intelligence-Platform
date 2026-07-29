import math


def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    return len(set(retrieved[:k]) & relevant) / len(relevant)


def precision_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    return len(set(retrieved[:k]) & relevant) / k


def reciprocal_rank(retrieved: list[str], relevant: set[str]) -> float:
    for rank, item in enumerate(retrieved, 1):
        if item in relevant:
            return 1 / rank
    return 0.0


def ndcg_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if not relevant or k <= 0:
        return 0.0
    dcg = sum(
        1 / math.log2(rank + 1) for rank, item in enumerate(retrieved[:k], 1) if item in relevant
    )
    ideal_count = min(len(relevant), k)
    ideal = sum(1 / math.log2(rank + 1) for rank in range(1, ideal_count + 1))
    return dcg / ideal


def retrieval_summary(runs: list[tuple[list[str], set[str]]]) -> dict[str, float]:
    if not runs:
        return {
            "recall_at_1": 0.0,
            "recall_at_3": 0.0,
            "recall_at_5": 0.0,
            "mrr": 0.0,
            "ndcg_at_5": 0.0,
        }
    count = len(runs)
    return {
        "recall_at_1": sum(recall_at_k(items, relevant, 1) for items, relevant in runs) / count,
        "recall_at_3": sum(recall_at_k(items, relevant, 3) for items, relevant in runs) / count,
        "recall_at_5": sum(recall_at_k(items, relevant, 5) for items, relevant in runs) / count,
        "mrr": sum(reciprocal_rank(items, relevant) for items, relevant in runs) / count,
        "ndcg_at_5": sum(ndcg_at_k(items, relevant, 5) for items, relevant in runs) / count,
    }
