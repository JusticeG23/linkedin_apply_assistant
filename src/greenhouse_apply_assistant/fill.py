"""Small, value-safe helpers for post-fill reconciliation."""

from typing import Any, Dict, Mapping, Tuple


# Exact local facts only. Sensitive work-authorization, sponsorship, employment,
# citizenship, and consent questions intentionally stay outside this mapping.
_PROFILE_CONTROLS = {
    "first_name": "first_name",
    "last_name": "last_name",
    "email": "email",
    "phone": "phone",
    "candidate-location": "city",
}


def fill_explicit_profile_facts(page: Any, profile: Mapping[str, Any]) -> Dict[str, str]:
    """Fill only whitelisted direct profile facts into empty hosted-form inputs.

    Return control IDs and statuses only; never return or log field values.
    """
    outcomes: Dict[str, str] = {}
    expected: Dict[str, str] = {}
    for control_id, profile_key in _PROFILE_CONTROLS.items():
        value = profile.get(profile_key)
        if not isinstance(value, str) or not value:
            continue
        locator = page.locator(f"#{control_id}")
        if locator.count() != 1 or locator.input_value() != "":
            outcomes[control_id] = "skipped"
            continue
        locator.fill(value)
        expected[control_id] = value
    # Re-read all controls after last fill; later widget updates can reset an
    # earlier value, so per-keystroke confirmation is insufficient.
    for control_id, value in expected.items():
        locator = page.locator(f"#{control_id}")
        outcomes[control_id] = (
            "verified"
            if locator.count() == 1 and locator.input_value() == value
            else "mismatch"
        )
    return outcomes


def readback_mismatches(
    expected: Mapping[str, str], observed: Mapping[str, str]
) -> Tuple[str, ...]:
    """Return field IDs whose rendered value differs from expected value.

    Do not include field values in failures or diagnostics; they may contain
    private applicant data.
    """
    return tuple(sorted(
        field_id
        for field_id, expected_value in expected.items()
        if observed.get(field_id) != expected_value
    ))
