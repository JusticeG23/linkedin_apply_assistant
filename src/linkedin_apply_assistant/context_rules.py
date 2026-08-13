from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

try:
    import yaml
except ModuleNotFoundError:  # Allows smoke tests before project dependencies are installed.
    yaml = None

try:
    from rapidfuzz import fuzz
except ModuleNotFoundError:  # Keep smoke tests usable before dependencies install.
    fuzz = None


@dataclass
class ContextRuleMatch:
    rule: str
    anchor: str
    phrase: str
    score: float
    reject: bool

    @property
    def reason(self) -> str:
        return f"context rule: {self.rule} via {self.anchor!r}/{self.phrase!r}"


def load_context_rules(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        content = fh.read()
    if yaml is None:
        return {}
    data = yaml.safe_load(content)
    if not isinstance(data, dict):
        raise ValueError(f"Context rules file must contain a mapping: {path}")
    return data


def evaluate_context_rules(
    text: str,
    rules: dict[str, Any],
    threshold: int = 85,
    window: int = 160,
) -> list[ContextRuleMatch]:
    matches: list[ContextRuleMatch] = []
    lower = (text or "").lower()
    for rule_name, rule in rules.items():
        if not isinstance(rule, dict):
            continue
        for anchor in rule.get("anchors", []):
            for start in _anchor_positions(lower, str(anchor).lower(), threshold):
                context = lower[max(0, start - window) : min(len(lower), start + len(str(anchor)) + window)]
                if _matches_any(context, rule.get("soft_context", []), threshold):
                    continue
                required_match = _best_match(context, rule.get("required_context", []), threshold)
                if required_match is None:
                    continue
                phrase, score = required_match
                matches.append(
                    ContextRuleMatch(
                        rule=rule_name,
                        anchor=str(anchor),
                        phrase=phrase,
                        score=score,
                        reject=bool(rule.get("reject", True)),
                    )
                )
    return matches


def _anchor_positions(text: str, anchor: str, threshold: int) -> list[int]:
    if not anchor:
        return []
    positions = []
    start = 0
    while True:
        idx = text.find(anchor, start)
        if idx < 0:
            break
        positions.append(idx)
        start = idx + len(anchor)
    return positions


def _matches_any(text: str, phrases: list[str], threshold: int) -> bool:
    return _best_match(text, phrases, threshold) is not None


def _best_match(text: str, phrases: list[str], threshold: int) -> Optional[tuple[str, float]]:
    best: Optional[tuple[str, float]] = None
    for phrase in phrases:
        score = _score(text, str(phrase).lower())
        if score < threshold:
            continue
        if best is None or score > best[1]:
            best = (str(phrase), score)
    return best


def _score(text: str, phrase: str) -> float:
    if not phrase:
        return 0
    if phrase in text:
        return 100
    if fuzz is None:
        return 0
    return float(fuzz.partial_ratio(text, phrase))
