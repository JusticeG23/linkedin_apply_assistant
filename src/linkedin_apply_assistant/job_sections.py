from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class JobSection:
    kind: str
    header: str
    text: str


HEADER_KINDS: dict[str, str] = {
    "about the job": "overview",
    "about the company": "overview",
    "responsibilities": "responsibilities",
    "what you'll do": "responsibilities",
    "what you’ll do": "responsibilities",
    "the role": "responsibilities",
    "basic qualifications": "required",
    "minimum qualifications": "required",
    "minimum requirements": "required",
    "required qualifications": "required",
    "requirements": "required",
    "what we're looking for": "required",
    "what we’re looking for": "required",
    "qualifications": "qualifications",
    "preferred qualifications": "preferred",
    "bonus points": "preferred",
    "nice to have": "preferred",
    "suggested skills": "preferred",
}

NESTED_HEADER_KINDS: dict[str, str] = {
    "about the team": "overview",
    "about wealthfront engineering": "overview",
    "about you": "required",
    "you will": "responsibilities",
    "you'll": "responsibilities",
    "you’ll": "responsibilities",
    "what you will do": "responsibilities",
    "what you'll do": "responsibilities",
    "what you’ll do": "responsibilities",
    "you have": "required",
    "you should have": "required",
    "we're looking for": "required",
    "we’re looking for": "required",
    "what you bring": "required",
    "required experience": "required",
    "minimum experience": "required",
    "bonus": "preferred",
    "nice to have": "preferred",
    "preferred experience": "preferred",
}

_HEADER_RE = re.compile(
    r"(?i)(?<!\w)("
    + "|".join(re.escape(header) for header in sorted(HEADER_KINDS, key=len, reverse=True))
    + r")(?!\w)\s*:?"
)

_NESTED_HEADER_RE = re.compile(
    r"(?i)(?<!\w)("
    + "|".join(re.escape(header) for header in sorted(NESTED_HEADER_KINDS, key=len, reverse=True))
    + r")(?!\w)\s*:?"
)


def split_job_sections(text: str) -> list[JobSection]:
    """Split noisy LinkedIn job text into broad semantic sections."""
    normalized = _normalize_text(text)
    if not normalized:
        return []

    matches = [match for match in _HEADER_RE.finditer(normalized) if _looks_like_header(match.group(1))]
    if not matches:
        return _split_nested_sections(normalized) or [JobSection(kind="unknown", header="", text=normalized)]

    sections: list[JobSection] = []
    if matches[0].start() > 0:
        sections.append(JobSection(kind="overview", header="", text=normalized[: matches[0].start()].strip()))

    for idx, match in enumerate(matches):
        header = match.group(1)
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(normalized)
        body = normalized[start:end].strip()
        if not body:
            continue
        sections.append(JobSection(kind=_kind_for_header(header), header=header, text=body))

    if len(sections) <= 1:
        nested = _split_nested_sections(sections[0].text if sections else normalized)
        if len(nested) > 1:
            return nested

    return sections


def section_text(sections: list[JobSection], kinds: set[str]) -> str:
    return " ".join(section.text for section in sections if section.kind in kinds)


def section_headers(sections: list[JobSection], kinds: set[str]) -> list[str]:
    return [section.header for section in sections if section.kind in kinds and section.header]


def _normalize_text(text: str) -> str:
    return " ".join((text or "").split())


def _kind_for_header(header: str) -> str:
    return HEADER_KINDS[header.lower()]


def _nested_kind_for_header(header: str) -> str:
    return NESTED_HEADER_KINDS[header.lower()]


def _split_nested_sections(text: str) -> list[JobSection]:
    matches = [
        match
        for match in _NESTED_HEADER_RE.finditer(text)
        if _looks_like_header(match.group(1)) and _looks_like_nested_boundary(text, match.start())
    ]
    if not matches:
        return []
    matches = _prefer_broad_required_section(matches)

    sections: list[JobSection] = []
    if matches[0].start() > 0:
        sections.append(JobSection(kind="overview", header="", text=text[: matches[0].start()].strip()))

    for idx, match in enumerate(matches):
        header = match.group(1)
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if not body:
            continue
        sections.append(JobSection(kind=_nested_kind_for_header(header), header=header, text=body))

    return sections


def _prefer_broad_required_section(matches: list[re.Match]) -> list[re.Match]:
    about_you = next((match for match in matches if match.group(1).lower() == "about you"), None)
    if not about_you:
        return matches
    return [
        match
        for match in matches
        if match.start() < about_you.start() or match.group(1).lower() != "you have"
    ]


def _looks_like_nested_boundary(text: str, start: int) -> bool:
    if start == 0:
        return True
    prefix = text[max(0, start - 4):start]
    if any(char in prefix for char in ".:;•"):
        return True
    previous = text[:start].rstrip()
    return previous.endswith((")", "]"))


def _looks_like_header(header: str) -> bool:
    # Avoid matching sentence fragments like "required for the role" or
    # "qualifications, skills" after whitespace normalization removes newlines.
    return bool(header and (header[0].isupper() or header.isupper()))
