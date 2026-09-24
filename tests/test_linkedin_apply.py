from linkedin_apply_assistant.linkedin_apply import _is_step_label


def test_step_label_does_not_treat_back_as_forward():
    assert _is_step_label("Go back", {"next", "continue", "review"}) is False
    assert _is_step_label("Back to previous step", {"next", "continue", "review"}) is False


def test_step_label_accepts_forward_actions():
    assert _is_step_label("Continue to next step", {"next", "continue", "review"}) is True
    assert _is_step_label("Review your application", {"next", "continue", "review"}) is True
    assert _is_step_label("Submit application", {"submit application"}) is True
