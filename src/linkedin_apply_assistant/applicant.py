from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ApplicantProfile:
    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    email: str = ""
    phone: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    work_authorized_us: bool | None = None
    needs_sponsorship: bool | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "ApplicantProfile":
        return cls(
            first_name=str(data.get("first_name") or "").strip(),
            last_name=str(data.get("last_name") or "").strip(),
            full_name=str(data.get("full_name") or "").strip(),
            email=str(data.get("email") or "").strip(),
            phone=str(data.get("phone") or "").strip(),
            city=str(data.get("city") or "").strip(),
            state=str(data.get("state") or "").strip(),
            country=str(data.get("country") or "").strip(),
            work_authorized_us=_optional_bool(data.get("work_authorized_us")),
            needs_sponsorship=_optional_bool(data.get("needs_sponsorship")),
        )

    @property
    def display_name(self) -> str:
        return self.full_name or " ".join(part for part in [self.first_name, self.last_name] if part)


def load_applicant_profile(path: Path) -> ApplicantProfile:
    if not path.exists():
        raise FileNotFoundError(f"Applicant config not found: {path}")
    data = yaml.safe_load(path.read_text()) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Applicant config must be a YAML mapping: {path}")
    return ApplicantProfile.from_mapping(data)


def resolve_resume_path(resume_root: Path, resume_family: str) -> Path:
    family_dir = resume_root / resume_family
    if not family_dir.exists():
        raise FileNotFoundError(f"Resume family folder not found: {family_dir}")

    pdfs = sorted(path for path in family_dir.glob("*.pdf") if path.is_file())
    if not pdfs:
        raise FileNotFoundError(f"No PDF resume found in: {family_dir}")

    family_tokens = {token for token in resume_family.lower().split("_") if token}
    scored = sorted(
        pdfs,
        key=lambda path: (
            -sum(1 for token in family_tokens if token in path.stem.lower()),
            len(path.name),
            path.name,
        ),
    )
    return scored[0]


def answer_for_label(label: str, applicant: ApplicantProfile) -> str | None:
    normalized = _normalize_label(label)
    if not normalized:
        return None

    if _mentions(normalized, "first", "name") and applicant.first_name:
        return applicant.first_name
    if _mentions(normalized, "last", "name") and applicant.last_name:
        return applicant.last_name
    if ("full name" in normalized or normalized == "name") and applicant.display_name:
        return applicant.display_name
    if ("email" in normalized or "e-mail" in normalized) and applicant.email:
        return applicant.email
    if ("phone" in normalized or "mobile" in normalized) and applicant.phone:
        return applicant.phone
    if ("city" in normalized or "current location" in normalized) and applicant.city:
        return applicant.city
    if _mentions(normalized, "state") and applicant.state:
        return applicant.state
    if _mentions(normalized, "country") and applicant.country:
        return applicant.country

    if _is_work_auth_label(normalized) and applicant.work_authorized_us is not None:
        return "Yes" if applicant.work_authorized_us else "No"
    if _is_sponsorship_label(normalized) and applicant.needs_sponsorship is not None:
        return "Yes" if applicant.needs_sponsorship else "No"

    return None


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    lowered = str(value).strip().lower()
    if lowered in {"true", "yes", "y", "1"}:
        return True
    if lowered in {"false", "no", "n", "0"}:
        return False
    return None


def _normalize_label(label: str) -> str:
    return " ".join(str(label or "").lower().replace("*", " ").split())


def _mentions(text: str, *terms: str) -> bool:
    return all(term in text for term in terms)


def _is_work_auth_label(label: str) -> bool:
    return (
        ("authorized" in label or "authorised" in label or "eligible" in label)
        and ("work" in label or "employment" in label or "united states" in label or "u.s." in label or "us" in label)
    )


def _is_sponsorship_label(label: str) -> bool:
    return "sponsor" in label or "sponsorship" in label or "visa" in label
