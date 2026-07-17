from app.evaluation.generation_metrics import exact_match, token_f1
from app.evaluation.retrieval_metrics import recall_at_k


def test_generation_metrics():
    assert exact_match("Paris", "paris") == 1.0 and token_f1("Paris France", "Paris") > 0.6


def test_recall():
    assert recall_at_k(["a", "b"], {"b", "c"}, 2) == 0.5
