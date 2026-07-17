# Evaluation

Evaluation accepts question and expected-answer pairs. The current runner records normalized
exact match, token F1, and answer rate. Add retrieval relevance labels to calculate recall@k,
precision@k, and reciprocal rank using `app/evaluation/retrieval_metrics.py`.
