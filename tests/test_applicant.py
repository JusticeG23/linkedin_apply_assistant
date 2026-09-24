from pathlib import Path

import pytest

from linkedin_apply_assistant.applicant import (
    ApplicantProfile,
    answer_for_label,
    load_applicant_profile,
    resolve_resume_path,
)


def test_load_applicant_profile(tmp_path: Path):
    path = tmp_path / "applicant.yaml"
    path.write_text(
        """
first_name: Justice
last_name: Garner
email: justice@example.com
work_authorized_us: yes
needs_sponsorship: no
"""
    )

    profile = load_applicant_profile(path)

    assert profile.first_name == "Justice"
    assert profile.last_name == "Garner"
    assert profile.work_authorized_us is True
    assert profile.needs_sponsorship is False


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("First name", "Justice"),
        ("Last name", "Garner"),
        ("Email address", "justice@example.com"),
        ("Mobile phone number", "206-643-1563"),
        ("Current location", "Mountain View"),
        ("Are you legally authorized to work in the United States?", "Yes"),
        ("Will you now or in the future require visa sponsorship?", "No"),
    ],
)
def test_answer_for_label(label: str, expected: str):
    profile = ApplicantProfile(
        first_name="Justice",
        last_name="Garner",
        email="justice@example.com",
        phone="206-643-1563",
        city="Mountain View",
        work_authorized_us=True,
        needs_sponsorship=False,
    )

    assert answer_for_label(label, profile) == expected


def test_answer_for_label_does_not_guess_free_text():
    profile = ApplicantProfile(first_name="Justice")

    assert answer_for_label("Why are you interested in this role?", profile) is None


def test_resolve_resume_path_prefers_matching_family_tokens(tmp_path: Path):
    family = tmp_path / "backend_engineer"
    family.mkdir()
    (family / "Justice_Garner_Resume.pdf").write_text("generic")
    expected = family / "Justice_Garner_Backend_Engineer_Resume.pdf"
    expected.write_text("backend")

    assert resolve_resume_path(tmp_path, "backend_engineer") == expected


def test_resolve_resume_path_errors_without_pdf(tmp_path: Path):
    (tmp_path / "backend_engineer").mkdir()

    with pytest.raises(FileNotFoundError):
        resolve_resume_path(tmp_path, "backend_engineer")
