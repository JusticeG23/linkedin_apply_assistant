from linkedin_apply_assistant.context_rules import evaluate_context_rules


RULES = {
    "degree_required": {
        "reject": True,
        "anchors": ["phd", "doctorate", "advanced degree"],
        "required_context": ["required", "requirement", "mandatory"],
        "soft_context": ["preferred", "bonus", "equivalent experience"],
        "required_section_match": True,
    },
    "data_science_required": {
        "reject": True,
        "anchors": ["data science", "statistical modeling"],
        "required_context": ["required", "must have"],
        "soft_context": ["partner with data science"],
    },
}


def test_exact_anchor_prevents_computer_science_false_positive():
    matches = evaluate_context_rules("Minimum requirement: PhD in computer science.", RULES)
    reasons = [match.reason for match in matches]
    assert any("degree_required" in reason for reason in reasons)
    assert not any("data_science_required" in reason for reason in reasons)


def test_soft_context_suppresses_reject():
    matches = evaluate_context_rules("Preferred: PhD or equivalent experience.", RULES)
    assert matches == []


def test_anchor_in_required_section_can_reject_without_required_word_nearby():
    matches = evaluate_context_rules("PhD in Computer Science, Mathematics, Statistics, or related field.", RULES)
    assert any(match.rule == "degree_required" for match in matches)
