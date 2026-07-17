"""Report worker pipeline adapter."""

from app.agents.report_writer import write_report
from app.models.domain import RetrievedEvidence


def build_report(question: str, answer: str, evidence: list[RetrievedEvidence]) -> str:
    """Build a Markdown report from a grounded answer and its evidence."""
    return write_report(question, answer, evidence)
