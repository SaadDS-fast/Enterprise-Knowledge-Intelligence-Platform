from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from app.models.domain import RetrievedEvidence
from app.rag.evidence import normalize_answer_value


@dataclass(frozen=True, slots=True)
class TopicItem:
    label: str
    confidence: str
    support_status: str
    chunk_id: UUID
    document_id: UUID
    document_title: str
    excerpt: str
    section: str | None

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "confidence": self.confidence,
            "support_status": self.support_status,
            "chunk_id": str(self.chunk_id),
            "document_id": str(self.document_id),
            "document_title": self.document_title,
            "excerpt": self.excerpt[:500],
            "section": self.section,
        }


TOPIC_LIST_TERMS = {
    "chapters",
    "covered",
    "cover",
    "covers",
    "list",
    "practice questions",
    "question",
    "questions",
    "subjects",
    "topics",
    "units",
}

TOPIC_LABEL_RE = re.compile(
    r"(?im)^\s*(?:#{1,6}\s*)?(?:section|topic|chapter|unit|subject)\s*[:=-]\s*"
    r"(?P<label>[A-Za-z][A-Za-z0-9 &'/-]{1,80})\s*$"
)
COMPACT_TOPIC_LABEL_RE = re.compile(
    r"(?i)\b(?:section|topic|chapter|unit|subject)\s*[:=-]\s*"
    r"(?P<label>[A-Za-z][A-Za-z0-9 &'/-]{1,80}?)"
    r"\s+(?:question|q)\s*\d+[A-Za-z]?\s*[:.)-]"
)
QUESTION_RE = re.compile(r"(?im)^\s*(?:question|q)\s*(?P<number>\d+[A-Za-z]?)\s*[:.)-]")
RAW_FRAGMENT_RE = re.compile(r"[=^]|[a-z][A-Z]|\d\s*[+\-*/]\s*\d")


def is_topic_list_query(query: str) -> bool:
    normalized = re.sub(r"\s+", " ", query).strip().lower()
    if not normalized:
        return False
    asks_list = bool(re.search(r"\b(what|which|list|name|identify)\b", normalized))
    topicish = any(term in normalized for term in TOPIC_LIST_TERMS)
    question_context = "practice question" in normalized or "questions" in normalized
    return (
        asks_list
        and topicish
        and (question_context or "topic" in normalized or "chapter" in normalized)
    )


def discover_topic_items(evidence: list[RetrievedEvidence]) -> list[TopicItem]:
    items: list[TopicItem] = []
    seen: set[str] = set()
    for item in sorted(enumerate(evidence), key=_document_order):
        item = item[1]
        for label in _explicit_labels(item.content):
            key = _topic_key(label)
            if key in seen:
                continue
            seen.add(key)
            items.append(
                TopicItem(
                    label=label,
                    confidence="high",
                    support_status="SUPPORTED",
                    chunk_id=item.chunk_id,
                    document_id=item.document_id,
                    document_title=item.document_title,
                    excerpt=item.content,
                    section=str((item.metadata or {}).get("section") or "") or None,
                )
            )
    return items


def _document_order(indexed: tuple[int, RetrievedEvidence]) -> tuple[int, int]:
    index, item = indexed
    ordinal = (item.metadata or {}).get("ordinal")
    return (ordinal if isinstance(ordinal, int) else index, index)


def has_practice_questions(evidence: list[RetrievedEvidence]) -> bool:
    return any(QUESTION_RE.search(item.content) for item in evidence)


def synthesize_topic_list(items: list[TopicItem]) -> str:
    lines = ["The practice questions cover:"]
    for index, item in enumerate(items, 1):
        section = f", {item.section}" if item.section and item.section != item.label else ""
        lines.append(f"{index}. {item.label} - supported by {item.document_title}{section}.")
    return "\n".join(lines)


def topic_list_abstention_message() -> str:
    return (
        "The questions were retrieved, but their topic labels cannot be determined confidently "
        "from the extracted document structure. Add section, topic, chapter, unit, or subject "
        "headings, or use Ollama-assisted classification in a later phase."
    )


def _explicit_labels(content: str) -> list[str]:
    labels: list[str] = []
    for match in TOPIC_LABEL_RE.finditer(content):
        label = normalize_answer_value(match.group("label"))
        if _valid_topic_label(label):
            labels.append(label)
    for match in COMPACT_TOPIC_LABEL_RE.finditer(content):
        label = normalize_answer_value(match.group("label"))
        if _valid_topic_label(label):
            labels.append(label)
    return labels


def _valid_topic_label(label: str) -> bool:
    if not 2 <= len(label) <= 80:
        return False
    if RAW_FRAGMENT_RE.search(label):
        return False
    lowered = label.lower()
    return not any(
        marker in lowered
        for marker in (
            "ignore previous",
            "system instructions",
            "developer message",
            "chain-of-thought",
            "calculate velocity",
            "determine whether",
        )
    )


def _topic_key(label: str) -> str:
    return re.sub(r"\W+", " ", label).strip().lower()
