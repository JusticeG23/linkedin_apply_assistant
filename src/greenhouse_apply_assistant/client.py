"""Strict URL parsing and read-only Greenhouse Job Board API access."""

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


_JOB_URL = re.compile(
    r"https://(?:boards|job-boards)\.greenhouse\.io/([A-Za-z0-9_-]+)/jobs/([0-9]+)/?"
)
_API_BASE = "https://boards-api.greenhouse.io/v1/boards"


class GreenhouseError(Exception):
    """Base class for Greenhouse inspection failures."""


class InvalidJobUrlError(GreenhouseError, ValueError):
    """Input is not an approved hosted Greenhouse job URL."""


class FetchError(GreenhouseError):
    """Read-only API request failed."""


class InvalidResponseError(GreenhouseError):
    """API response did not match expected job/questions contract."""


@dataclass(frozen=True)
class JobUrl:
    board_token: str
    job_id: int
    original_url: str


@dataclass(frozen=True)
class GreenhouseJob:
    board_token: str
    job_id: int
    job_url: str
    questions: Tuple[Any, ...]
    payload: Dict[str, Any]


def parse_job_url(value: str) -> JobUrl:
    """Parse only exact hosted-board job URLs; reject all alternate forms."""
    if not isinstance(value, str):
        raise InvalidJobUrlError("job URL must be a string")

    match = _JOB_URL.fullmatch(value)
    if match is None:
        raise InvalidJobUrlError(
            "expected https://boards.greenhouse.io/{board_token}/jobs/{numeric_job_id} "
            "or https://job-boards.greenhouse.io/{board_token}/jobs/{numeric_job_id}"
        )

    board_token, job_id_text = match.groups()
    job_id = int(job_id_text)
    if job_id <= 0:
        raise InvalidJobUrlError("job ID must be a positive numeric ID")

    return JobUrl(board_token=board_token, job_id=job_id, original_url=value)


def fetch_greenhouse_job(job_url: str, timeout: float = 10.0) -> GreenhouseJob:
    """Fetch one job and application questions using GET only.

    No application submission endpoint is used by this module.
    """
    parsed = parse_job_url(job_url)
    api_url = (
        f"{_API_BASE}/{parsed.board_token}/jobs/{parsed.job_id}?questions=true"
    )
    request = Request(
        api_url,
        headers={"Accept": "application/json"},
        method="GET",
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            response_body = response.read()
    except (HTTPError, URLError, OSError, TimeoutError) as exc:
        raise FetchError(f"Greenhouse job fetch failed: {exc}") from exc

    try:
        payload = json.loads(response_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidResponseError("API response is not valid UTF-8 JSON") from exc

    if not isinstance(payload, dict):
        raise InvalidResponseError("API response must be a JSON object")

    response_id = payload.get("id")
    if isinstance(response_id, bool) or not isinstance(response_id, (int, str)):
        raise InvalidResponseError("API response must include a numeric matching job id")
    if isinstance(response_id, str) and re.fullmatch(r"[0-9]+", response_id) is None:
        raise InvalidResponseError("API response must include a numeric matching job id")
    try:
        response_job_id = int(response_id)
    except ValueError as exc:
        raise InvalidResponseError(
            "API response must include a numeric matching job id"
        ) from exc
    if response_job_id != parsed.job_id:
        raise InvalidResponseError(
            f"API response job id {response_job_id} does not match requested job {parsed.job_id}"
        )

    if "questions" not in payload:
        raise InvalidResponseError("API response is missing questions")
    questions = payload["questions"]
    if not isinstance(questions, list):
        raise InvalidResponseError("API response questions must be a JSON array")

    return GreenhouseJob(
        board_token=parsed.board_token,
        job_id=parsed.job_id,
        job_url=parsed.original_url,
        questions=tuple(questions),
        payload=payload,
    )
