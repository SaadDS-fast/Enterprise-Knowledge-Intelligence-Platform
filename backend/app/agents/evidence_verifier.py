from app.models.domain import RetrievedEvidence
from app.rag.evidence import evidence_is_sufficient


def verify(question: str, evidence: list[RetrievedEvidence]) -> bool:
    return evidence_is_sufficient(
        [item.score for item in evidence], question, [item.content for item in evidence]
    )
