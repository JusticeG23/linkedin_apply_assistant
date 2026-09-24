from greenhouse_apply_assistant.fill import (
    fill_explicit_profile_facts,
    readback_mismatches,
)


class FakeLocator:
    def __init__(self, value="", on_fill=None):
        self.value = value
        self.on_fill = on_fill

    def count(self):
        return 1

    def input_value(self):
        return self.value

    def fill(self, value):
        self.value = value
        if self.on_fill:
            self.on_fill()


class FakePage:
    def __init__(self, reset_phone_on_city=False):
        self.controls = {key: FakeLocator() for key in (
            "first_name", "last_name", "email", "phone", "candidate-location",
            "question_immigration",
        )}
        if reset_phone_on_city:
            self.controls["candidate-location"].on_fill = (
                lambda: setattr(self.controls["phone"], "value", "")
            )

    def locator(self, selector):
        return self.controls[selector.removeprefix("#")]


def test_profile_fill_whitelist_ignores_sensitive_and_user_specific_controls():
    page = FakePage()

    outcomes = fill_explicit_profile_facts(page, {
        "first_name": "Synthetic",
        "last_name": "Applicant",
        "email": "synthetic@example.test",
        "phone": "000",
        "city": "Test City",
        "work_authorized_us": True,
        "needs_sponsorship": False,
        "question_immigration": "No",
    })

    assert outcomes == {
        "first_name": "verified",
        "last_name": "verified",
        "email": "verified",
        "phone": "verified",
        "candidate-location": "verified",
    }
    assert page.controls["question_immigration"].input_value() == ""


def test_fill_rechecks_earlier_fields_after_later_widget_changes():
    page = FakePage(reset_phone_on_city=True)

    outcomes = fill_explicit_profile_facts(page, {
        "first_name": "Synthetic",
        "last_name": "Applicant",
        "email": "synthetic@example.test",
        "phone": "000",
        "city": "Test City",
    })

    assert outcomes["phone"] == "mismatch"


def test_fill_values_are_verified_by_readback_without_echoing_values():
    expected = {"application:email": "synthetic@example.test", "application:phone": "000"}
    observed = {"application:email": "synthetic@example.test", "application:phone": "111"}

    assert readback_mismatches(expected, observed) == ("application:phone",)
    assert readback_mismatches(expected, expected) == ()
