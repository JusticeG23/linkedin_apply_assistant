from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Optional

from .criteria import required_min_yoe_for_job
from .job_sections import split_job_sections
from .models import Job


DEFAULT_MODEL = "gpt-4.1-mini"
RESPONSES_URL = "https://api.openai.com/v1/responses"


@dataclass(frozen=True)
class LlmJudgment:
    decision: str
    confidence: str
    role_family: str
    reason: str


def build_judge_payload(job: Job) -> dict[str, Any]:
    """Build the small, clean payload sent to the LLM judge."""
    sections = split_job_sections(job.description)
    return {
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "work_mode": job.work_mode,
        "salary_text": job.salary_text,
        "easy_apply": job.easy_apply,
        "normalized_signals": {
            "required_yoe_min": required_min_yoe_for_job(job),
            "yoe_note": "For ranges like 3-7 years or 2-12+ years, treat the lower bound as the minimum required years.",
        },
        "required_sections": [
            {
                "header": section.header or "Overview",
                "body": section.text,
            }
            for section in sections
            if section.kind in {"required", "qualifications"}
        ],
    }


def judge_job_with_llm(
    job: Job,
    *,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    debug: bool = False,
    timeout_seconds: int = 30,
) -> LlmJudgment:
    """Ask an LLM to separate required gaps from preferred/noisy mentions."""
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    payload = build_judge_payload(job)
    if not payload["required_sections"]:
        raise RuntimeError("No required/minimum qualification sections found for LLM check")

    request_body = {
        "model": model or os.environ.get("OPENAI_MODEL", DEFAULT_MODEL),
        "input": [
            {
                "role": "system",
                "content": (
                    "You evaluate LinkedIn job postings for a candidate. "
                    "Return only valid JSON. Do not include markdown."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                    "candidate_constraints": {
                            "target_roles": [
                                "software engineer",
                                "backend",
                                "data engineer",
                                "data platform",
                                "infrastructure",
                                "reliability",
                                "full stack",
                            ],
                            "max_required_yoe": 5,
                            "avoid_required_skills": [
                                "data science",
                                "statistical modeling",
                                "ML research",
                                "PhD",
                                "TensorFlow",
                                "PyTorch",
                                "frontend-only",
                            ],
                        },
                        "interpretation_rules": [
                            "Only evaluate the provided required/minimum qualification sections for hard gaps.",
                            "For experience ranges like 3-7 years or 2-12+ years, treat the lower bound as the minimum required years.",
                            "Do not mark the upper bound of an experience range as a hard gap.",
                            "Only put skills in hard_gaps when they are clearly required by the provided sections.",
                            "Do not infer preferred gaps because preferred sections are intentionally omitted to reduce tokens.",
                        ],
                        "job": payload,
                        "required_output_shape": {
                            "decision": "needs_review | rejected",
                            "confidence": "low | medium | high",
                            "role_family": "short role family",
                            "reason": "one short sentence; include the hard skill gap if rejected",
                        },
                    },
                    separators=(",", ":"),
                ),
            },
        ],
        "text": {"format": {"type": "json_object"}},
    }
    if debug:
        print("LLM request JSON:")
        print(json.dumps(request_body, indent=2))

    request = urllib.request.Request(
        RESPONSES_URL,
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw_body = response.read().decode("utf-8")
            if debug:
                print("LLM raw response:")
                print(raw_body)
            raw_response = json.loads(raw_body)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"LLM request failed: {exc}; {_http_error_body(exc)}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"LLM request failed: {exc}") from exc

    raw_text = _response_text(raw_response)
    if debug:
        print("LLM response text:")
        print(raw_text)
    return parse_judgment(raw_text)


def parse_judgment(raw_text: str) -> LlmJudgment:
    data = json.loads(raw_text)
    reason = str(data.get("reason", ""))
    hard_gaps = [str(item) for item in data.get("hard_gaps", [])]
    if hard_gaps and reason and not any(gap.lower() in reason.lower() for gap in hard_gaps):
        reason = f"{reason} Hard gap: {', '.join(hard_gaps)}."
    return LlmJudgment(
        decision=str(data.get("decision", "needs_review")),
        confidence=str(data.get("confidence", "medium")),
        role_family=str(data.get("role_family", "")),
        reason=reason,
    )


def _response_text(response: dict[str, Any]) -> str:
    if response.get("output_text"):
        return str(response["output_text"])

    # Responses API payloads are nested; keep this parser narrow and explicit.
    for item in response.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                return str(content["text"])
    raise RuntimeError("LLM response did not include output text")


def _http_error_body(exc: urllib.error.HTTPError) -> str:
    body = exc.read().decode("utf-8", errors="replace")
    if not body:
        return "empty error body"
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return body[:500]
    message = data.get("error", {}).get("message")
    code = data.get("error", {}).get("code")
    if message and code:
        return f"{message} ({code})"
    if message:
        return str(message)
    return body[:500]
