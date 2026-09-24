import io
import json
from unittest.mock import patch
from urllib.request import Request

import pytest

from greenhouse_apply_assistant import (
    FetchError,
    GreenhouseJob,
    InvalidJobUrlError,
    InvalidResponseError,
    fetch_greenhouse_job,
    parse_job_url,
)


class MockResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.body


@pytest.mark.parametrize(
    "url",
    [
        "http://boards.greenhouse.io/acme/jobs/123",
        "https://boards.greenhouse.io.evil.test/acme/jobs/123",
        "https://boards.greenhouse.io@evil.test/acme/jobs/123",
        "https://user@boards.greenhouse.io/acme/jobs/123",
        "https://boards.greenhouse.io:443/acme/jobs/123",
        "https://boards.greenhouse.io/acme/jobs/123?source=share",
        "https://job-boards.greenhouse.io/acme/jobs/123?source=share",
        "https://boards.greenhouse.io/acme/jobs/123#apply",
        "https://boards.greenhouse.io/acme/jobs/123/anything",
        "https://boards.greenhouse.io/acme/123",
        "https://boards.greenhouse.io/jobs/123",
        "https://boards.greenhouse.io/acme/jobs/not-a-number",
        "https://boards.greenhouse.io/acme/jobs/0",
        "https://boards.greenhouse.io/acme/jobs/12%33",
        " https://boards.greenhouse.io/acme/jobs/123",
    ],
)
def test_rejects_unapproved_or_invalid_job_urls(url):
    with pytest.raises(InvalidJobUrlError):
        parse_job_url(url)


@pytest.mark.parametrize(
    ("url", "board_token", "job_id"),
    [
        ("https://boards.greenhouse.io/acme/jobs/123", "acme", 123),
        ("https://boards.greenhouse.io/acme-board_2/jobs/456/", "acme-board_2", 456),
        ("https://job-boards.greenhouse.io/twitch/jobs/8817023002", "twitch", 8817023002),
    ],
)
def test_parses_approved_job_url(url, board_token, job_id):
    parsed = parse_job_url(url)
    assert (parsed.board_token, parsed.job_id, parsed.original_url) == (
        board_token,
        job_id,
        url,
    )


def test_fetches_questions_with_exact_read_only_get_request():
    body = json.dumps(
        {"id": 123, "title": "Engineer", "questions": [{"label": "Name"}]}
    ).encode()

    def fake_urlopen(request, timeout):
        assert isinstance(request, Request)
        assert request.full_url == (
            "https://boards-api.greenhouse.io/v1/boards/acme/jobs/123?questions=true"
        )
        assert request.get_method() == "GET"
        assert timeout == 4.5
        return MockResponse(body)

    with patch("greenhouse_apply_assistant.client.urlopen", side_effect=fake_urlopen):
        result = fetch_greenhouse_job("https://boards.greenhouse.io/acme/jobs/123", 4.5)

    assert isinstance(result, GreenhouseJob)
    assert result.board_token == "acme"
    assert result.job_id == 123
    assert result.questions == ({"label": "Name"},)
    assert result.payload["title"] == "Engineer"


def test_invalid_url_never_starts_request():
    with patch("greenhouse_apply_assistant.client.urlopen") as urlopen:
        with pytest.raises(InvalidJobUrlError):
            fetch_greenhouse_job("https://greenhouse.io/acme/jobs/123")
    urlopen.assert_not_called()


@pytest.mark.parametrize(
    "body",
    [
        b"not-json",
        json.dumps([{"id": 123, "questions": []}]).encode(),
        json.dumps({"id": 123}).encode(),
        json.dumps({"id": 123, "questions": None}).encode(),
        json.dumps({"id": "not-numeric", "questions": []}).encode(),
        json.dumps({"id": " 123", "questions": []}).encode(),
        json.dumps({"id": 124, "questions": []}).encode(),
        json.dumps({"id": True, "questions": []}).encode(),
    ],
)
def test_rejects_invalid_api_payloads(body):
    with patch(
        "greenhouse_apply_assistant.client.urlopen", return_value=MockResponse(body)
    ):
        with pytest.raises(InvalidResponseError):
            fetch_greenhouse_job("https://boards.greenhouse.io/acme/jobs/123")


def test_wraps_transport_errors():
    with patch(
        "greenhouse_apply_assistant.client.urlopen", side_effect=OSError("offline")
    ):
        with pytest.raises(FetchError, match="offline"):
            fetch_greenhouse_job("https://boards.greenhouse.io/acme/jobs/123")
