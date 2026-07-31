"""Deterministic answer plans and immutable critical-fact registries."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.llm.grounded import INJECTION_PATTERN, EvidencePacketItem
from app.rag.embeddings import tokenize

FACT_PATTERN = re.compile(
    r"(?i)(?:\b(?:PKR|USD|EUR|GBP)\s*[\d,.]+(?:\s+per\s+\w+)?|"
    r"\b\d+(?:\.\d+)?\s*(?:%|percent|percentage points?|kg|km|days?|months?|years?)\b|"
    r"\b\d{1,2}\s+[A-Za-z]+\s+\d{4}\b|"
    r"\b[a-z]\w*\s*[²^]\s*\d?\s*[+\-=≠≤≥][^,.!?;]*|"
    r"\b(?:must not|must|may not|cannot|current|superseded|effective|published)\b)"
)
ROLE_PATTERN = re.compile(
    r"(?i)\b(?:finance director|operations director|department manager|line manager|"
    r"chief executive officer|project owner)\b"
)
NAME_PATTERN = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b")


@dataclass(frozen=True, slots=True)
class LockedFact:
    fact_id: str
    text: str
    fact_type: str
    evidence_id: str
    canonical_value: str | None = None
    currency: str | None = None
    unit: str | None = None
    frequency: str | None = None
    limit_type: str | None = None
    date_type: str | None = None


@dataclass(frozen=True, slots=True)
class RequiredComponent:
    component_id: str
    text: str
    evidence_ids: tuple[str, ...]
    fact_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AnswerPlan:
    query_intent: str
    components: tuple[RequiredComponent, ...]
    facts: tuple[LockedFact, ...]
    composite: bool


def build_answer_plan(question: str, packet: list[EvidencePacketItem]) -> AnswerPlan:
    question_tokens = set(tokenize(question))
    candidates: list[tuple[float, int, str, EvidencePacketItem]] = []
    for evidence_index, item in enumerate(packet):
        for sentence_index, raw in enumerate(re.split(r"(?<=[.!?])\s+|\n+", item.text)):
            sentence = " ".join(raw.split())
            if len(sentence) < 8 or INJECTION_PATTERN.search(sentence):
                continue
            sentence_tokens = set(tokenize(sentence))
            overlap = len(question_tokens & sentence_tokens) / max(1, len(question_tokens))
            candidates.append((overlap, -(evidence_index * 100 + sentence_index), sentence, item))
    candidates.sort(reverse=True, key=lambda row: (row[0], row[1]))
    multi = bool(
        re.search(
            r"(?i)\b(list|compare|comparison|both|all|two|and who|and what|multi|composite)\b",
            question,
        )
    )
    selected = candidates[: min(8, len(candidates))] if multi else candidates[:1]
    selected.sort(key=lambda row: -row[1])
    facts: list[LockedFact] = []
    components: list[RequiredComponent] = []
    for component_index, (_, _, sentence, item) in enumerate(selected, 1):
        component_fact_ids: list[str] = []
        matches = list(FACT_PATTERN.finditer(sentence))
        matches.extend(ROLE_PATTERN.finditer(sentence))
        matches.extend(NAME_PATTERN.finditer(sentence))
        seen: set[str] = set()
        for match in sorted(matches, key=lambda value: value.start()):
            text = match.group(0).strip()
            key = text.casefold()
            if key in seen:
                continue
            seen.add(key)
            fact_id = f"F{len(facts) + 1}"
            attributes = _fact_attributes(text, sentence)
            facts.append(
                LockedFact(
                    fact_id=fact_id,
                    text=text,
                    fact_type=_fact_type(text),
                    evidence_id=item.evidence_id,
                    **attributes,
                )
            )
            component_fact_ids.append(fact_id)
        components.append(
            RequiredComponent(
                component_id=f"R{component_index}",
                text=sentence,
                evidence_ids=(item.evidence_id,),
                fact_ids=tuple(component_fact_ids),
            )
        )
    return AnswerPlan(
        query_intent="multi_component" if multi else "direct",
        components=tuple(components),
        facts=tuple(facts),
        composite=len({value for item in components for value in item.evidence_ids}) > 1,
    )


def _fact_type(text: str) -> str:
    lowered = text.casefold()
    if re.search(r"\b(?:pkr|usd|eur|gbp)\b", lowered):
        return "money"
    if re.search(r"\b(?:effective|published)\b|\d{1,2}\s+[a-z]+\s+\d{4}", lowered):
        return "date_or_applicability"
    if ROLE_PATTERN.fullmatch(text):
        return "role"
    if NAME_PATTERN.fullmatch(text):
        return "entity"
    if re.search(r"[=²^]", text):
        return "equation"
    if re.search(r"\b(?:must|may|cannot)\b", lowered):
        return "obligation"
    return "quantity"


def _fact_attributes(text: str, sentence: str) -> dict[str, str | None]:
    lowered = text.casefold()
    currency_match = re.search(r"(?i)\b(PKR|USD|EUR|GBP)\b", text)
    value_match = re.search(r"\d+(?:[,.]\d+)*", text)
    frequency_match = re.search(r"(?i)\bper\s+(day|month|year|week)\b", text)
    unit_match = re.search(r"(?i)\b(percentage points?|percent|kg|km|days?|months?|years?)\b", text)
    date_type_match = re.search(r"(?i)\b(effective|published|approval|expiry|review)\b", sentence)
    limit_type_match = re.search(r"(?i)\b(maximum|minimum|limit|allowance|rate|budget)\b", sentence)
    canonical = value_match.group(0).replace(",", "") if value_match else None
    if "%" in text:
        unit = "percent"
    else:
        unit = unit_match.group(1).casefold() if unit_match else None
    return {
        "canonical_value": canonical,
        "currency": currency_match.group(1).upper() if currency_match else None,
        "unit": unit,
        "frequency": frequency_match.group(1).casefold() if frequency_match else None,
        "limit_type": limit_type_match.group(1).casefold() if limit_type_match else None,
        "date_type": (
            date_type_match.group(1).casefold()
            if date_type_match and ("date" in sentence.casefold() or "202" in lowered)
            else None
        ),
    }
