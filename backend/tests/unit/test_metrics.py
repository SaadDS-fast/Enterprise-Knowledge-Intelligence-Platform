from app.evaluation.generation_metrics import exact_match, token_f1
from app.evaluation.retrieval_metrics import ndcg_at_k, recall_at_k, retrieval_summary


def test_generation_metrics():
    assert exact_match("Paris", "paris") == 1.0 and token_f1("Paris France", "Paris") > 0.6


def test_recall():
    assert recall_at_k(["a", "b"], {"b", "c"}, 2) == 0.5


def test_ranked_retrieval_summary():
    metrics = retrieval_summary([(["relevant", "other"], {"relevant"})])
    assert metrics == {
        "recall_at_1": 1.0,
        "recall_at_3": 1.0,
        "recall_at_5": 1.0,
        "mrr": 1.0,
        "ndcg_at_5": 1.0,
    }
    assert 0 < ndcg_at_k(["other", "relevant"], {"relevant"}, 5) < 1
