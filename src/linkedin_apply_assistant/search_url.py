from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from .criteria import yaml


WORK_TYPE_CODES = {
    "remote": "2",
    "hybrid": "3",
    "onsite": "1",
}

EXPERIENCE_CODES = {
    "internship": "1",
    "entry": "2",
    "associate": "3",
    "mid_senior": "4",
    "director": "5",
    "executive": "6",
}


def load_search_presets(path: Path) -> dict[str, dict[str, Any]]:
    if yaml is None:
        raise RuntimeError("Search presets require PyYAML. Run: pip install -e .")
    with path.open("r", encoding="utf-8") as fh:
        presets = yaml.safe_load(fh)
    if not isinstance(presets, dict):
        raise ValueError(f"Search preset file must contain a mapping: {path}")
    return presets


def build_linkedin_search_url(preset: dict[str, Any]) -> str:
    work_type = _codes_from_names(preset.get("work_type", []), WORK_TYPE_CODES, "work_type")
    experience = _codes_from_names(preset.get("experience", []), EXPERIENCE_CODES, "experience")

    params = {
        "keywords": preset["keywords"],
        "location": preset["location"],
        "distance": str(preset.get("distance", 10)),
        "sortBy": preset.get("sort_by", "DD"),
    }
    if preset.get("easy_apply", True):
        params["f_AL"] = "true"
    if preset.get("posted_within"):
        params["f_TPR"] = str(preset["posted_within"])
    if work_type:
        params["f_WT"] = ",".join(work_type)
    if experience:
        params["f_E"] = ",".join(experience)

    # doseq is intentionally false because LinkedIn expects comma-joined filter
    # values in one parameter, such as f_WT=1,3 for onsite + hybrid.
    return "https://www.linkedin.com/jobs/search/?" + urlencode(params)


def _codes_from_names(names: list[str], mapping: dict[str, str], field_name: str) -> list[str]:
    codes: list[str] = []
    for name in names:
        key = str(name).lower()
        if key not in mapping:
            allowed = ", ".join(sorted(mapping))
            raise ValueError(f"Unknown {field_name} value {name!r}; allowed: {allowed}")
        codes.append(mapping[key])
    return codes
