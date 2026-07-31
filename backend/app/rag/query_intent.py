from __future__ import annotations

import re
from enum import StrEnum


class QueryIntent(StrEnum):
    FACT = "FACT"
    DEFINITION = "DEFINITION"
    LIST = "LIST"
    TOPIC_IDENTIFICATION = "TOPIC_IDENTIFICATION"
    COMPARISON = "COMPARISON"
    MULTI_EVIDENCE = "MULTI_EVIDENCE"
    DOCUMENT_IDENTIFICATION = "DOCUMENT_IDENTIFICATION"
    KNOWLEDGE_ABSENCE_PROBE = "KNOWLEDGE_ABSENCE_PROBE"
    AMBIGUOUS = "AMBIGUOUS"


def classify_query_intent(query: str) -> QueryIntent:
    normalized = " ".join(query.lower().split()).strip(" ?")
    terms = set(re.findall(r"[a-z0-9]+", normalized))
    if terms & {"prohibited", "forbidden", "required", "allowed", "obligation"}:
        return QueryIntent.FACT
    if len(terms) <= 1 or normalized in {"status", "project", "policy", "atlas"}:
        return QueryIntent.AMBIGUOUS
    if re.search(r"\b(compare|difference|versus|vs)\b", normalized):
        return QueryIntent.COMPARISON
    if re.search(r"\b(and|as well as|from both|across)\b", normalized):
        return QueryIntent.MULTI_EVIDENCE
    if re.search(r"\b(list|enumerate|which (?:items|topics|questions))\b", normalized):
        return QueryIntent.LIST
    if re.search(r"\b(topic|subject|about)\b", normalized):
        return QueryIntent.TOPIC_IDENTIFICATION
    if re.search(r"\b(which|what) (?:document|policy|file)\b", normalized):
        return QueryIntent.DOCUMENT_IDENTIFICATION
    if re.search(r"\b(define|definition|meaning|what is|guarantees)\b", normalized):
        return QueryIntent.DEFINITION
    if terms & {"revenue", "profit", "turnover"}:
        return QueryIntent.KNOWLEDGE_ABSENCE_PROBE
    return QueryIntent.FACT
