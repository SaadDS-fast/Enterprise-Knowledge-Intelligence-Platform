"""Typed, deterministic guards for terminology-sensitive retrieval.

The rules describe reusable concept families rather than benchmark sentences.  They
are deliberately conservative: a missing synonym is a small penalty, while an
explicitly contradictory sibling concept is a large penalty.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class ConceptKind(StrEnum):
    NUMERIC_ATTRIBUTE = "numeric_attribute"
    SCIENTIFIC_CONCEPT = "scientific_concept"
    ALLOWANCE_TYPE = "allowance_type"
    APPROVAL_PROCESS = "approval_process"
    ROLE = "role"
    MATHEMATICAL_OBJECT = "mathematical_object"
    DATE_TYPE = "date_type"
    POLICY_STATE = "policy_state"


@dataclass(frozen=True, slots=True)
class Concept:
    kind: ConceptKind
    name: str
    terms: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ConceptAssessment:
    required: tuple[str, ...]
    matched: tuple[str, ...]
    contradictions: tuple[str, ...]
    coverage: float
    score_adjustment: float
    eligible_support: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "required": list(self.required),
            "matched": list(self.matched),
            "contradictions": list(self.contradictions),
            "coverage": round(self.coverage, 4),
            "score_adjustment": round(self.score_adjustment, 4),
            "eligible_support": self.eligible_support,
        }


CONCEPT_FAMILIES: tuple[tuple[Concept, ...], ...] = (
    (
        Concept(ConceptKind.NUMERIC_ATTRIBUTE, "revenue", ("revenue", "sales income")),
        Concept(ConceptKind.NUMERIC_ATTRIBUTE, "budget", ("budget", "spending plan")),
        Concept(ConceptKind.NUMERIC_ATTRIBUTE, "profit", ("profit", "net income")),
    ),
    (
        Concept(
            ConceptKind.SCIENTIFIC_CONCEPT,
            "deformation",
            ("deformation", "elasticity", "elastic", "strain", "extension"),
        ),
        Concept(
            ConceptKind.SCIENTIFIC_CONCEPT,
            "motion",
            ("motion", "velocity", "displacement", "acceleration", "particle movement"),
        ),
        Concept(ConceptKind.SCIENTIFIC_CONCEPT, "force", ("force", "load", "newton")),
    ),
    (
        Concept(
            ConceptKind.ALLOWANCE_TYPE,
            "travel allowance",
            ("travel allowance", "travel stipend", "per diem"),
        ),
        Concept(
            ConceptKind.ALLOWANCE_TYPE,
            "leave allowance",
            ("leave allowance", "vacation allowance", "paid leave"),
        ),
        Concept(
            ConceptKind.ALLOWANCE_TYPE,
            "medical allowance",
            ("medical allowance", "health allowance"),
        ),
    ),
    (
        Concept(
            ConceptKind.APPROVAL_PROCESS,
            "procurement approval",
            ("procurement approval", "purchase approval", "tender approval"),
        ),
        Concept(
            ConceptKind.APPROVAL_PROCESS,
            "travel approval",
            ("travel approval", "trip approval", "travel authorization"),
        ),
    ),
    (
        Concept(ConceptKind.ROLE, "finance director", ("finance director",)),
        Concept(ConceptKind.ROLE, "department manager", ("department manager",)),
        Concept(ConceptKind.ROLE, "travel manager", ("travel manager",)),
        Concept(ConceptKind.ROLE, "procurement manager", ("procurement manager",)),
    ),
    (
        Concept(ConceptKind.MATHEMATICAL_OBJECT, "function", ("function", "mapping")),
        Concept(ConceptKind.MATHEMATICAL_OBJECT, "equation", ("equation", "equality")),
    ),
    (
        Concept(
            ConceptKind.DATE_TYPE,
            "effective date",
            ("effective date", "takes effect", "effective from"),
        ),
        Concept(
            ConceptKind.DATE_TYPE,
            "launch date",
            ("launch date", "launched on", "rollout date"),
        ),
        Concept(
            ConceptKind.DATE_TYPE,
            "publication date",
            ("publication date", "published on", "issued on"),
        ),
    ),
    (
        Concept(
            ConceptKind.POLICY_STATE,
            "current",
            ("current policy", "active policy", "currently effective"),
        ),
        Concept(
            ConceptKind.POLICY_STATE,
            "superseded",
            ("superseded", "archived policy", "former policy", "obsolete"),
        ),
    ),
)


def assess_concept_constraints(
    query: str,
    content: str,
    *,
    title: str = "",
    heading: str = "",
    metadata: dict | None = None,
) -> ConceptAssessment:
    query_text = _normalize(query)
    body = _normalize(" ".join((title, heading, content)))
    required: list[Concept] = []
    contradictions: list[str] = []
    matched: list[str] = []
    for family in CONCEPT_FAMILIES:
        requested = [concept for concept in family if _mentions(query_text, concept.terms)]
        for concept in requested:
            required.append(concept)
            concept_matched = _mentions(body, concept.terms)
            if concept_matched:
                matched.append(concept.name)
            else:
                for sibling in family:
                    if sibling != concept and _mentions(body, sibling.terms):
                        contradictions.append(sibling.name)

    metadata = metadata or {}
    if any(item.name == "current" for item in required) and _metadata_is_superseded(metadata):
        contradictions.append("superseded")

    names = tuple(dict.fromkeys(item.name for item in required))
    matches = tuple(dict.fromkeys(matched))
    conflicts = tuple(dict.fromkeys(contradictions))
    coverage = len(matches) / len(names) if names else 1.0
    structural_match = bool(
        heading and any(_mentions(_normalize(heading), item.terms) for item in required)
    )
    adjustment = (0.10 * coverage if names else 0.0) + (0.05 if structural_match else 0.0)
    adjustment -= 0.12 * (len(names) - len(matches))
    adjustment -= 0.24 * len(conflicts)
    return ConceptAssessment(
        required=names,
        matched=matches,
        contradictions=conflicts,
        coverage=coverage,
        score_adjustment=max(-0.6, min(0.2, adjustment)),
        eligible_support=not names or (coverage == 1.0 and not conflicts),
    )


def _mentions(text: str, terms: tuple[str, ...]) -> bool:
    return any(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text) for term in terms)


def _normalize(text: str) -> str:
    return " ".join(text.lower().replace("_", " ").replace("-", " ").split())


def _metadata_is_superseded(metadata: dict) -> bool:
    state = str(
        metadata.get("policy_state")
        or metadata.get("version_state")
        or metadata.get("status")
        or ""
    ).lower()
    return state in {"superseded", "archived", "obsolete", "inactive"}
