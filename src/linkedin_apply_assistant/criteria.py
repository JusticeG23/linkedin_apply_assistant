from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

try:
    import yaml
except ModuleNotFoundError:  # Allows smoke tests before project dependencies are installed.
    yaml = None

from .models import Job, JobStatus
from .context_rules import evaluate_context_rules


# LinkedIn cards often abbreviate salary as "$200k-$350k"; normalize that
# into one estimated base value for filtering.
MONEY_SUFFIX_BOUNDARY = r"(?![\dA-Za-z])(?!(?:\s*(?:[mM]\b|million|billion)))"
COMP_RE = re.compile(rf"\$\s*(\d+(?:,\d{{3}})?)([kK])?{MONEY_SUFFIX_BOUNDARY}")
COMP_RANGE_RE = re.compile(
    rf"\$\s*(\d+(?:,\d{{3}})?)([kK])?{MONEY_SUFFIX_BOUNDARY}(?:\s*(?:/yr|/year|a year))?"
    rf"\s*[-–—]\s*\$?\s*(\d+(?:,\d{{3}})?)([kK])?{MONEY_SUFFIX_BOUNDARY}(?:\s*(?:/yr|/year|a year))?",
    re.I,
)
YOE_RANGE_RE = re.compile(r"(?<![\d.])(\d{1,2})\s*[-–]\s*(\d{1,2})\s*(?:years|yrs|year)", re.I)
YOE_PLUS_RE = re.compile(r"(?<![\d.])(\d{1,2})\s*\+?\s*(?:years|yrs|year)", re.I)

HYBRID_TERMS = ["hybrid"]


def load_criteria(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        content = fh.read()
    if yaml is not None:
        return yaml.safe_load(content)
    return _load_simple_yaml(content)


def _load_simple_yaml(content: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_list_key: Optional[str] = None
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- ") and current_list_key:
            data[current_list_key].append(line[2:].strip())
            continue
        current_list_key = None
        if line.endswith(":"):
            current_list_key = line[:-1]
            data[current_list_key] = []
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if value.isdigit():
            data[key.strip()] = int(value)
            continue
        try:
            data[key.strip()] = float(value)
        except ValueError:
            data[key.strip()] = value
    return data


def _contains_any(text: str, terms: list[str]) -> list[str]:
    lower = text.lower()
    return [term for term in terms if term.lower() in lower]


def _extract_money_values(text: str) -> list[int]:
    values: list[int] = []
    for match in COMP_RE.finditer(text or ""):
        amount = int(match.group(1).replace(",", ""))
        if match.group(2):
            amount *= 1000
        values.append(amount)
    return values


def _normalize_money(amount_text: str, suffix: Optional[str]) -> int:
    amount = int(amount_text.replace(",", ""))
    if suffix:
        amount *= 1000
    return amount


def _extract_first_money_range(text: str) -> Optional[tuple[int, int]]:
    match = COMP_RANGE_RE.search(text or "")
    if not match:
        return None
    low = _normalize_money(match.group(1), match.group(2))
    high = _normalize_money(match.group(3), match.group(4))
    return low, high


def _required_min_yoe(text: str) -> Optional[int]:
    requirements = []

    # For ranges like "3-7 years", the hard requirement is the lower bound.
    # Keep the maximum across requirements because a posting may also say
    # something stricter elsewhere, such as "8+ years in production systems."
    for match in YOE_RANGE_RE.finditer(text or ""):
        requirements.append(int(match.group(1)))

    text_without_ranges = YOE_RANGE_RE.sub("", text or "")
    for match in YOE_PLUS_RE.finditer(text_without_ranges):
        requirements.append(int(match.group(1)))

    return max(requirements) if requirements else None


def _location_allowed(job: Job, criteria: dict[str, Any], full_text: str) -> bool:
    allowed_locations = criteria.get("allowed_locations", [])
    if _contains_any(job.location, allowed_locations):
        return True

    hybrid_locations = criteria.get("hybrid_allowed_locations", [])
    is_hybrid = bool(_contains_any(full_text, HYBRID_TERMS))
    return is_hybrid and bool(_contains_any(job.location, hybrid_locations))


def estimate_base(job: Job) -> Optional[int]:
    text = " ".join([job.salary_text, job.description])
    money_range = _extract_first_money_range(text)
    if money_range:
        return int(sum(money_range) / 2)

    values = _extract_money_values(text)
    if not values:
        return None
    return values[0]


def classify_job(job: Job, criteria: dict[str, Any], context_rules: Optional[dict[str, Any]] = None) -> Job:
    full_text = " ".join([job.title, job.company, job.location, job.salary_text, job.description])
    title_text = " ".join([job.title, job.company])

    reject_reasons: list[str] = []
    score = 0

    if not job.easy_apply:
        reject_reasons.append("not Easy Apply")

    allowed_locations = criteria.get("allowed_locations", [])
    if allowed_locations and not _location_allowed(job, criteria, full_text):
        reject_reasons.append(f"location outside target band: {job.location}")

    # This must run against the detailed job text when available; cards often
    # omit qualification lines like "8+ years of experience."
    hard_yoe = _required_min_yoe(full_text)
    max_yoe = int(criteria.get("max_required_yoe", 5))
    if hard_yoe and hard_yoe > max_yoe:
        reject_reasons.append(f"hard YOE appears too high: {hard_yoe}+")

    bad_roles = _contains_any(title_text, criteria.get("reject_role_terms", []))
    if bad_roles:
        reject_reasons.append("role mismatch: " + ", ".join(bad_roles))

    hard_gaps = _contains_any(full_text, criteria.get("hard_gap_terms", []))
    if hard_gaps:
        reject_reasons.append("hard skill gap: " + ", ".join(hard_gaps[:3]))

    for match in evaluate_context_rules(full_text, context_rules or {}):
        if match.reject:
            reject_reasons.append(match.reason)

    # Normalize salary ranges to one base-pay decision value. Keep the legacy
    # storage field name for compatibility; output labels it as estimated base.
    min_base = int(criteria.get("target_min_base", 200000))
    estimated_base = estimate_base(job)
    job.estimated_tc = estimated_base

    if estimated_base and estimated_base < min_base:
        reject_reasons.append(f"estimated base below target: {estimated_base}")

    allowed_terms = _contains_any(title_text, criteria.get("allowed_role_terms", []))
    score += 10 * len(allowed_terms)

    company_terms = _contains_any(job.company, criteria.get("preferred_company_terms", []))
    full_terms = _contains_any(full_text, criteria.get("preferred_company_terms", []))
    score += 5 * len(set(company_terms + full_terms))

    if any(term in full_text.lower() for term in ["ai", "llm", "infrastructure", "platform", "distributed"]):
        score += 10

    job.score = score
    if reject_reasons:
        job.status = JobStatus.REJECTED
        job.reject_reason = "; ".join(reject_reasons)
    else:
        job.status = JobStatus.NEEDS_REVIEW
        notes = []
        if allowed_terms:
            notes.append("role terms: " + ", ".join(allowed_terms))
        if estimated_base:
            notes.append(f"estimated base: ${estimated_base:,}")
        job.fit_notes = "; ".join(notes)
    return job
