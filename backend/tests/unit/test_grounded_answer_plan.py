from uuid import uuid4

from app.llm.answer_plan import build_answer_plan
from app.llm.grounded import build_evidence_packet
from app.llm.grounded_v2 import (
    GroundedCandidateV2,
    normalize_candidate_payload,
    verify_and_render,
)
from app.models.domain import RetrievedEvidence


def packet(text: str):
    evidence = RetrievedEvidence(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_title="Synthetic Policy",
        content=text,
        score=0.99,
        metadata={"section": "Current policy"},
    )
    return build_evidence_packet([evidence])


def candidate_for(plan, *, omit_last: bool = False):
    components = plan.components[:-1] if omit_last else plan.components
    return GroundedCandidateV2.model_validate(
        {
            "answer_segments": [
                {
                    "segment_id": f"S{index}",
                    "text": "supported connector",
                    "required_component_id": item.component_id,
                    "fact_ids": list(item.fact_ids),
                    "evidence_ids": list(item.evidence_ids),
                }
                for index, item in enumerate(components, 1)
            ],
            "claims": [
                {
                    "claim_id": f"C{index}",
                    "required_component_id": item.component_id,
                    "fact_ids": list(item.fact_ids),
                    "evidence_ids": list(item.evidence_ids),
                }
                for index, item in enumerate(components, 1)
            ],
            "used_evidence_ids": ["E1"],
            "insufficient_support": False,
        }
    )


def test_money_and_frequency_are_locked_and_rendered_server_side():
    evidence = packet("The meal allowance is PKR 6,250 per day.")
    plan = build_answer_plan("What is the meal allowance?", evidence)
    assert {fact.text for fact in plan.facts} >= {"PKR 6,250 per day"}
    money = next(fact for fact in plan.facts if fact.fact_type == "money")
    assert money.canonical_value == "6250"
    assert money.currency == "PKR"
    assert money.frequency == "day"
    assert money.limit_type == "allowance"
    result = verify_and_render(candidate_for(plan), plan, evidence)
    assert result.passed
    assert result.answer == "The meal allowance is PKR 6,250 per day."


def test_equation_and_condition_are_preserved():
    evidence = packet("The equation is px² + qx + r = 0, where p must not be zero.")
    plan = build_answer_plan("What is the equation and condition?", evidence)
    result = verify_and_render(candidate_for(plan), plan, evidence)
    assert "px² + qx + r = 0" in result.answer
    assert "must not be zero" in result.answer


def test_missing_required_claim_is_completed_deterministically():
    evidence = packet("The owner is Sana Malik. The launch date is 12 April 2027.")
    plan = build_answer_plan("Who is the owner and what is the launch date?", evidence)
    result = verify_and_render(candidate_for(plan, omit_last=True), plan, evidence)
    assert result.passed
    assert result.category == "deterministic_claim_completion"
    assert len(result.missing_components) == 1
    assert "Sana Malik" in result.answer
    assert "12 April 2027" in result.answer


def test_unknown_fact_and_evidence_ids_fail_closed():
    evidence = packet("The approver is the department manager.")
    plan = build_answer_plan("Who approves?", evidence)
    raw = candidate_for(plan).model_dump()
    raw["answer_segments"][0]["fact_ids"] = ["F999"]
    assert not verify_and_render(GroundedCandidateV2.model_validate(raw), plan, evidence).passed
    raw = candidate_for(plan).model_dump()
    raw["answer_segments"][0]["evidence_ids"] = ["E999"]
    assert not verify_and_render(GroundedCandidateV2.model_validate(raw), plan, evidence).passed
    raw = candidate_for(plan).model_dump()
    raw["used_evidence_ids"] = ["E999"]
    assert not verify_and_render(GroundedCandidateV2.model_validate(raw), plan, evidence).passed


def test_model_text_cannot_replace_locked_role():
    evidence = packet("Travel is approved by the department manager.")
    plan = build_answer_plan("Who approves travel?", evidence)
    raw = candidate_for(plan).model_dump()
    raw["answer_segments"][0]["text"] = "The Finance Director approves travel."
    result = verify_and_render(GroundedCandidateV2.model_validate(raw), plan, evidence)
    assert "Finance Director" not in result.answer
    assert "department manager" in result.answer


def test_structural_normalization_uses_only_server_plan():
    evidence = packet("The meal allowance is PKR 6,250 per day.")
    plan = build_answer_plan("What is the meal allowance?", evidence)
    raw = {
        "answer_segments": [
            {
                "segment_id": "A1",
                "text": "PKR 99,999",
                "required_component_id": "R1",
                "fact_ids": ["F1"],
                "evidence_ids": ["E1"],
            }
        ],
        "claims": [],
        "used_evidence_ids": ["E1"],
        "insufficient_support": False,
    }
    normalized = normalize_candidate_payload(raw, plan)
    candidate = GroundedCandidateV2.model_validate(normalized)
    result = verify_and_render(candidate, plan, evidence)
    assert candidate.answer_segments[0].segment_id == "S1"
    assert candidate.claims[0].claim_id == "C1"
    assert "99,999" not in result.answer


def test_structural_normalization_discards_untrusted_ids_and_non_object_payload():
    evidence = packet("The meal allowance is PKR 6,250 per day.")
    plan = build_answer_plan("What is the meal allowance?", evidence)
    raw = {
        "answer_segments": [
            {
                "segment_id": "S99",
                "text": "invented",
                "required_component_id": "R1",
                "fact_ids": ["F999"],
                "evidence_ids": ["E999"],
            }
        ],
        "claims": [{"required_component_id": "R999"}],
        "used_evidence_ids": ["E999"],
        "insufficient_support": True,
    }
    candidate = GroundedCandidateV2.model_validate(normalize_candidate_payload(raw, plan))
    assert candidate.answer_segments[0].fact_ids == ["F1"]
    assert candidate.answer_segments[0].evidence_ids == ["E1"]
    assert candidate.used_evidence_ids == ["E1"]
    assert not candidate.insufficient_support

    repaired = GroundedCandidateV2.model_validate(normalize_candidate_payload([], plan))
    assert repaired.answer_segments[0].required_component_id == "R1"


def test_model_abstention_cannot_override_server_sufficiency_decision():
    evidence = packet("The meal allowance is PKR 6,250 per day.")
    plan = build_answer_plan("What is the meal allowance?", evidence)
    raw = candidate_for(plan).model_dump()
    raw["insufficient_support"] = True
    result = verify_and_render(GroundedCandidateV2.model_validate(raw), plan, evidence)
    assert result.passed
    assert result.answer == "The meal allowance is PKR 6,250 per day."
