from app.models.domain import RetrievedEvidence


def append_citations(answer: str, evidence: list[RetrievedEvidence]) -> str:
    if not evidence:
        return answer
    refs = "\n\nSources: " + ", ".join(
        f"[{i}] {item.document_title}" for i, item in enumerate(evidence, 1)
    )
    return answer.rstrip() + refs
