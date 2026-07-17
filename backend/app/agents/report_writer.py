from app.models.domain import RetrievedEvidence


def write_report(question: str, answer: str, evidence: list[RetrievedEvidence]) -> str:
    sources = "\n".join(f"- {item.document_title}: {item.score:.2f}" for item in evidence)
    return (
        f"# Research Report\n\n## Question\n{question}\n\n"
        f"## Answer\n{answer}\n\n## Sources\n{sources}"
    )
