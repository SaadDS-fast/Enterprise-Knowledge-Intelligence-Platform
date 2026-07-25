from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from app.core.config import settings

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "did",
    "does",
    "in",
    "is",
    "it",
    "its",
    "of",
    "the",
    "to",
    "was",
    "what",
    "when",
    "which",
    "who",
}


class SupportStatus(StrEnum):
    SUPPORTED = "SUPPORTED"
    PARTIAL = "PARTIAL"
    ABSENT = "ABSENT"
    CONFLICT = "CONFLICT"


class RequestedAttribute(StrEnum):
    TOPIC = "topic"
    DEFINITION = "definition"
    OWNER = "owner"
    DATE = "date"
    NUMERIC = "numeric"
    STATUS = "status"
    LOCATION = "location"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ExtractedFact:
    attribute: RequestedAttribute
    value: str
    source_index: int
    matched_text: str


@dataclass(frozen=True, slots=True)
class SupportAssessment:
    status: SupportStatus
    sufficient: bool
    attribute: RequestedAttribute
    answer_value: str | None
    support_score: float
    support_reasons: list[str]
    facts: list[ExtractedFact]
    conflict_values: list[str]

    def as_dict(self) -> dict:
        return {
            "status": self.status.value,
            "sufficient": self.sufficient,
            "attribute": self.attribute.value,
            "answer_value": self.answer_value,
            "support_score": round(self.support_score, 4),
            "support_reasons": self.support_reasons,
            "conflict_values": self.conflict_values,
        }


def key_terms(text: str) -> set[str]:
    return {
        token.strip(".,:;!?()[]{}\"'").lower()
        for token in text.split()
        if len(token.strip(".,:;!?()[]{}\"'")) >= 3
        and token.strip(".,:;!?()[]{}\"'").lower() not in STOPWORDS
    }


ATTRIBUTE_SYNONYMS: dict[RequestedAttribute, set[str]] = {
    RequestedAttribute.TOPIC: {"topic", "about", "covered", "covers", "subject"},
    RequestedAttribute.DEFINITION: {"definition", "define", "meaning", "what"},
    RequestedAttribute.OWNER: {"owner", "owns", "owned", "responsible", "accountable"},
    RequestedAttribute.DATE: {"when", "date", "launched", "started", "began", "deadline"},
    RequestedAttribute.NUMERIC: {"budget", "cost", "amount", "revenue", "allowance", "number"},
    RequestedAttribute.STATUS: {"status", "state", "approved", "enabled", "disabled"},
    RequestedAttribute.LOCATION: {"where", "location", "office", "region"},
}

ATTRIBUTE_LABELS: dict[RequestedAttribute, tuple[str, ...]] = {
    RequestedAttribute.TOPIC: ("demo topic", "topic", "subject"),
    RequestedAttribute.DEFINITION: ("definition", "meaning"),
    RequestedAttribute.OWNER: ("owner", "owned by", "responsible", "accountable"),
    RequestedAttribute.DATE: ("launch date", "date", "deadline", "started", "launched"),
    RequestedAttribute.NUMERIC: ("budget", "cost", "revenue", "allowance", "amount"),
    RequestedAttribute.STATUS: ("status", "state"),
    RequestedAttribute.LOCATION: ("location", "region", "office"),
}


def requested_attribute(query: str) -> RequestedAttribute:
    normalized = query.lower()
    terms = key_terms(query)
    if "topic" in terms or "demo topic" in normalized or "about" in terms:
        return RequestedAttribute.TOPIC
    if terms & {"owner", "owns", "owned", "responsible", "accountable"}:
        return RequestedAttribute.OWNER
    if terms & {"when", "date", "launched", "started", "began", "deadline"}:
        return RequestedAttribute.DATE
    if terms & {"budget", "cost", "amount", "revenue", "allowance"}:
        return RequestedAttribute.NUMERIC
    if terms & {"status", "approved", "enabled", "disabled", "active", "inactive"}:
        return RequestedAttribute.STATUS
    if terms & {"where", "location", "region", "office"}:
        return RequestedAttribute.LOCATION
    if "define" in normalized or normalized.startswith("what is "):
        return RequestedAttribute.DEFINITION
    return RequestedAttribute.UNKNOWN


def normalize_answer_value(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value).strip().strip(" .;")
    return normalized


def assess_evidence_support(
    scores: list[float], query: str, contents: list[str]
) -> SupportAssessment:
    attribute = requested_attribute(query)
    direct_facts = extract_facts(query, contents, attribute)
    query_terms = key_terms(query)
    evidence_terms = key_terms(" ".join(contents[:3]))
    coverage = len(query_terms & evidence_terms) / max(1, len(query_terms))
    max_score = max(scores, default=0.0)
    support_score = max(0.0, min(1.0, 0.55 * max_score + 0.35 * coverage))
    reasons: list[str] = []
    if max_score >= settings.evidence_min_score:
        reasons.append("retrieval_score")
    if coverage >= 0.34:
        reasons.append("query_term_coverage")
    compound_query = bool(re.search(r"\b(and|as well as|plus)\b", query, re.I))
    if direct_facts:
        reasons.append("direct_attribute_match")
        support_score = max(support_score, 0.82)
    if any(_heading_label_match(attribute, fact.matched_text) for fact in direct_facts):
        reasons.append("heading_value_pair")
        support_score = max(support_score, 0.9)
    distinct_values = _distinct_fact_values(direct_facts)
    if len(distinct_values) > 1 and attribute is not RequestedAttribute.UNKNOWN:
        return SupportAssessment(
            status=SupportStatus.CONFLICT,
            sufficient=False,
            attribute=attribute,
            answer_value=None,
            support_score=support_score,
            support_reasons=[*reasons, "conflicting_values"],
            facts=direct_facts,
            conflict_values=distinct_values,
        )
    globally_sufficient = max_score >= settings.evidence_min_score and coverage >= (
        0.75 if compound_query else 0.34
    )
    directly_supported = bool(direct_facts) and support_score >= 0.72 and not compound_query
    if globally_sufficient or directly_supported:
        return SupportAssessment(
            status=SupportStatus.SUPPORTED,
            sufficient=True,
            attribute=attribute,
            answer_value=direct_facts[0].value if direct_facts else None,
            support_score=support_score,
            support_reasons=reasons or ["supported_by_retrieval"],
            facts=direct_facts,
            conflict_values=[],
        )
    if contents and (coverage > 0 or max_score >= 0.28):
        return SupportAssessment(
            status=SupportStatus.PARTIAL,
            sufficient=False,
            attribute=attribute,
            answer_value=direct_facts[0].value if direct_facts else None,
            support_score=support_score,
            support_reasons=reasons or ["partial_query_overlap"],
            facts=direct_facts,
            conflict_values=[],
        )
    return SupportAssessment(
        status=SupportStatus.ABSENT,
        sufficient=False,
        attribute=attribute,
        answer_value=None,
        support_score=support_score,
        support_reasons=[],
        facts=[],
        conflict_values=[],
    )


def extract_facts(
    query: str, contents: list[str], attribute: RequestedAttribute | None = None
) -> list[ExtractedFact]:
    attribute = attribute or requested_attribute(query)
    if attribute is RequestedAttribute.UNKNOWN:
        return []
    facts: list[ExtractedFact] = []
    labels = ATTRIBUTE_LABELS[attribute]
    label_pattern = "|".join(re.escape(label) for label in sorted(labels, key=len, reverse=True))
    pair_re = re.compile(
        rf"(?im)^\s*(?:[-*]\s*)?(?:[A-Za-z0-9 &'/-]{{0,80}}\s+)?"
        rf"({label_pattern})\s*[:=-]\s*(?P<value>[^\n.;]{{1,160}})"
    )
    for index, content in enumerate(contents):
        for match in pair_re.finditer(content):
            value = normalize_answer_value(match.group("value"))
            if _valid_fact_value(value):
                facts.append(ExtractedFact(attribute, value, index, match.group(0).strip()))
        facts.extend(_sentence_facts(content, index, attribute))
    return _dedupe_facts(facts)


def synthesize_direct_answer(query: str, assessment: SupportAssessment) -> str | None:
    value = assessment.answer_value
    if not value:
        return None
    if assessment.attribute is RequestedAttribute.TOPIC:
        return f"The demo topic is {value}."
    if assessment.attribute is RequestedAttribute.OWNER:
        return f"The owner or responsible party is {value}."
    if assessment.attribute is RequestedAttribute.DATE:
        return f"The relevant date is {value}."
    if assessment.attribute is RequestedAttribute.NUMERIC:
        return f"The requested value is {value}."
    if assessment.attribute is RequestedAttribute.STATUS:
        return f"The status is {value}."
    if assessment.attribute is RequestedAttribute.LOCATION:
        return f"The location is {value}."
    if assessment.attribute is RequestedAttribute.DEFINITION:
        return value if value.endswith(".") else f"{value}."
    return None


def evidence_is_sufficient(scores: list[float], query: str, contents: list[str]) -> bool:
    return assess_evidence_support(scores, query, contents).sufficient


def _sentence_facts(content: str, index: int, attribute: RequestedAttribute) -> list[ExtractedFact]:
    facts: list[ExtractedFact] = []
    patterns: dict[RequestedAttribute, tuple[re.Pattern[str], ...]] = {
        RequestedAttribute.OWNER: (
            re.compile(
                r"\b(?:is\s+)?(?:owned by|owner is|accountable to|responsible for by)\s+"
                r"(?P<value>[A-Z][A-Za-z0-9 &-]{2,120})"
            ),
        ),
        RequestedAttribute.DATE: (
            re.compile(
                r"\b(?:launched|started|began|deadline is|date is)\s+"
                r"(?:on|in)?\s*(?P<value>(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
                r"[a-z]*\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{4})",
                re.I,
            ),
        ),
        RequestedAttribute.DEFINITION: (
            re.compile(r"\b(?P<value>A [^.]{10,240}\.)"),
            re.compile(r"\b(?P<value>An [^.]{10,240}\.)"),
        ),
    }
    for pattern in patterns.get(attribute, ()):
        for match in pattern.finditer(content):
            value = normalize_answer_value(match.group("value"))
            if _valid_fact_value(value):
                facts.append(ExtractedFact(attribute, value, index, match.group(0).strip()))
    return facts


def _dedupe_facts(facts: list[ExtractedFact]) -> list[ExtractedFact]:
    seen: set[tuple[RequestedAttribute, str]] = set()
    deduped: list[ExtractedFact] = []
    for fact in facts:
        key = (fact.attribute, _normalize_fact_key(fact.value))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(fact)
    return deduped


def _distinct_fact_values(facts: list[ExtractedFact]) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for fact in facts:
        key = _normalize_fact_key(fact.value)
        if key in seen:
            continue
        seen.add(key)
        values.append(fact.value)
    return values


def _normalize_fact_key(value: str) -> str:
    return re.sub(r"\W+", " ", value).strip().lower()


def _heading_label_match(attribute: RequestedAttribute, matched_text: str) -> bool:
    labels = ATTRIBUTE_LABELS.get(attribute, ())
    normalized = matched_text.lower()
    return any(re.search(rf"\b{re.escape(label)}\b\s*[:=-]", normalized) for label in labels)


def _valid_fact_value(value: str) -> bool:
    if not value:
        return False
    lowered = value.lower()
    if len(value) > 160:
        return False
    return not any(
        marker in lowered
        for marker in (
            "ignore previous",
            "system instructions",
            "developer message",
            "chain-of-thought",
        )
    )
