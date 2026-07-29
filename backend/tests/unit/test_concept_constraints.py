from app.rag.concept_constraints import assess_concept_constraints


def test_revenue_candidate_rejects_budget_hard_negative() -> None:
    correct = assess_concept_constraints(
        "What was annual revenue?",
        "Annual revenue: $18 million. Annual budget: $12 million.",
        heading="Financial Results",
    )
    wrong = assess_concept_constraints(
        "What was annual revenue?",
        "Annual budget: $12 million.",
        heading="Budget",
    )

    assert correct.eligible_support
    assert correct.score_adjustment > wrong.score_adjustment
    assert wrong.contradictions == ("budget",)


def test_material_deformation_rejects_particle_motion() -> None:
    correct = assess_concept_constraints(
        "Explain material deformation",
        "Elastic deformation is the reversible extension caused by a load.",
    )
    wrong = assess_concept_constraints(
        "Explain material deformation",
        "Particle motion describes velocity, displacement, and acceleration.",
    )

    assert correct.eligible_support
    assert not wrong.eligible_support
    assert "motion" in wrong.contradictions


def test_effective_date_is_distinct_from_launch_date() -> None:
    assessment = assess_concept_constraints(
        "What is the policy effective date?",
        "Launch date: 1 March 2026.",
    )

    assert not assessment.eligible_support
    assert assessment.required == ("effective date",)
    assert assessment.contradictions == ("launch date",)


def test_current_policy_uses_version_metadata() -> None:
    assessment = assess_concept_constraints(
        "What does the current policy require?",
        "Current policy travel rules.",
        metadata={"policy_state": "superseded"},
    )

    assert not assessment.eligible_support
    assert assessment.contradictions == ("superseded",)


def test_no_typed_concept_does_not_require_lexical_match() -> None:
    assessment = assess_concept_constraints(
        "Who owns the customer care handbook?",
        "The service lead is accountable for this guide.",
    )

    assert assessment.eligible_support
    assert assessment.score_adjustment == 0
