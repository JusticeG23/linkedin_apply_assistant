import json

from linkedin_apply_assistant.llm_judge import build_judge_payload, judge_job_with_llm, parse_judgment
from linkedin_apply_assistant.models import Job


def test_build_judge_payload_only_includes_required_sections():
    job = Job(
        job_id="1",
        title="Software Engineer",
        company="Example",
        location="Mountain View, CA",
        url="https://www.linkedin.com/jobs/view/1/",
        salary_text="$200k-$250k",
        work_mode="Hybrid",
        description=(
            "About the job Build backend platforms. "
            "Basic Qualifications 3+ years Python. "
            "Preferred Qualifications Kubernetes experience."
        ),
    )

    payload = build_judge_payload(job)

    assert payload["title"] == "Software Engineer"
    assert payload["salary_text"] == "$200k-$250k"
    assert payload["normalized_signals"]["required_yoe_min"] == 3
    assert [section["header"] for section in payload["required_sections"]] == ["Basic Qualifications"]
    assert "3+ years Python" in payload["required_sections"][0]["body"]
    assert "Kubernetes" not in payload["required_sections"][0]["body"]


def test_build_judge_payload_omits_sections_when_no_required_header():
    job = Job(
        job_id="1",
        title="Software Engineer",
        company="Example",
        location="Mountain View, CA",
        url="https://www.linkedin.com/jobs/view/1/",
        description="About the job Build backend platforms. Preferred Qualifications Kubernetes experience.",
    )

    payload = build_judge_payload(job)

    assert payload["required_sections"] == []


def test_parse_judgment_accepts_expected_json_shape():
    judgment = parse_judgment(json.dumps({
        "decision": "needs_review",
        "confidence": "high",
        "role_family": "backend platform",
        "reason": "Backend role with no hard required gaps.",
    }))

    assert judgment.decision == "needs_review"
    assert judgment.confidence == "high"
    assert judgment.role_family == "backend platform"
    assert judgment.reason == "Backend role with no hard required gaps."


def test_parse_judgment_keeps_old_hard_gap_response_readable():
    judgment = parse_judgment(json.dumps({
        "decision": "rejected",
        "role_family": "data science",
        "hard_gaps": ["required statistical modeling"],
        "reason": "Role requires data science depth.",
    }))

    assert judgment.confidence == "medium"
    assert judgment.reason == "Role requires data science depth. Hard gap: required statistical modeling."


def test_judge_debug_prints_request_and_response(monkeypatch, capsys):
    job = Job(
        job_id="1",
        title="Software Engineer",
        company="Example",
        location="Mountain View, CA",
        url="https://www.linkedin.com/jobs/view/1/",
        description="Minimum Requirements 3+ years Python.",
    )
    response = {
        "output_text": json.dumps({
            "decision": "needs_review",
            "confidence": "medium",
            "role_family": "backend",
            "reason": "No hard gaps.",
        })
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(response).encode("utf-8")

    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: FakeResponse())

    judgment = judge_job_with_llm(job, api_key="test-key", debug=True)

    output = capsys.readouterr().out
    assert judgment.decision == "needs_review"
    assert judgment.confidence == "medium"
    assert "LLM request JSON:" in output
    assert "LLM raw response:" in output
    assert "LLM response text:" in output
    assert "test-key" not in output
