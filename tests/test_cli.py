from linkedin_apply_assistant.cli import (
    _format_row,
    _truncate,
    preview_confidence,
    print_preview_report,
    print_section_debug,
    print_llm_judgment,
    review_jobs_for_commit,
    should_run_llm,
    to_tsv_row,
)
from linkedin_apply_assistant.llm_judge import LlmJudgment
from linkedin_apply_assistant.models import Job, JobStatus


def test_truncate_keeps_short_text_unchanged():
    assert _truncate("San Jose, CA", 50) == "San Jose, CA"


def test_truncate_shortens_long_text_with_ellipsis():
    text = "San Francisco Bay Area with a lot of noisy LinkedIn badge text"
    assert _truncate(text, 20) == "San Francisco Bay A…"


def test_format_row_uses_fixed_width_columns_before_url():
    row = _format_row(
        [
            "needs_review",
            "25",
            "backend_platform",
            "Very Long Software Engineer Title That Should Not Shift Everything",
            "Very Long Company Name That Also Needs A Cap",
            "San Francisco, CA",
            "$250,000",
            "matches software engineer; est base $250,000",
            "https://example.com/job",
        ],
        {
            "status": 12,
            "score": 5,
            "preset": 18,
            "title": 20,
            "company": 16,
            "location": 20,
            "base": 10,
            "why": 24,
        },
    )

    assert "Very Long Software…" in row
    assert "Very Long Compa…" in row
    assert row.endswith("https://example.com/job")


def test_review_jobs_for_commit_only_returns_approved_jobs(capsys):
    jobs = [
        Job(job_id="1", title="A", company="Example", location="Mountain View, CA", url="https://example.com/1"),
        Job(job_id="2", title="B", company="Example", location="Mountain View, CA", url="https://example.com/2"),
    ]
    answers = iter(["y", "n"])

    approved = review_jobs_for_commit(jobs, input_fn=lambda _: next(answers))

    assert [job.job_id for job in approved] == ["1"]
    assert "[1/2]" in capsys.readouterr().out


def test_review_jobs_for_commit_quit_returns_prior_approvals(capsys):
    jobs = [
        Job(job_id="1", title="A", company="Example", location="Mountain View, CA", url="https://example.com/1"),
        Job(job_id="2", title="B", company="Example", location="Mountain View, CA", url="https://example.com/2"),
    ]
    answers = iter(["y", "q"])

    approved = review_jobs_for_commit(jobs, input_fn=lambda _: next(answers))

    assert [job.job_id for job in approved] == ["1"]


def test_print_section_debug_shows_required_section(capsys):
    job = Job(
        job_id="1",
        title="Software Engineer",
        company="Example",
        location="Mountain View, CA",
        url="https://www.linkedin.com/jobs/view/1/",
        description="Minimum Requirements 3+ years Python. Preferred Qualifications Kubernetes.",
    )

    print_section_debug(job)

    output = capsys.readouterr().out
    assert "Extracted payload:" in output
    assert "required | Minimum Requirements" in output
    assert "3+ years Python" in output


def test_preview_report_includes_tsv_and_section_summary(capsys):
    job = Job(
        job_id="1",
        title="Software Engineer",
        company="Example",
        location="Mountain View, CA",
        url="https://www.linkedin.com/jobs/view/1/",
        easy_apply=True,
        salary_text="$200k-$250k",
        description="Minimum Requirements 3+ years Python. Preferred Qualifications Kubernetes.",
        status=JobStatus.NEEDS_REVIEW,
        estimated_tc=225000,
        fit_notes="matches software engineer",
    )

    print_preview_report(job)

    output = capsys.readouterr().out
    assert "Decision: needs_review" in output
    assert "Required sections:" in output
    assert "Preferred sections:" in output
    assert "TSV:" in output
    assert "Software Engineer\tExample\tMountain View, CA" in output


def test_should_run_llm_skips_cheap_rejects():
    job = Job(
        job_id="1",
        title="Software Engineer",
        company="Example",
        location="San Francisco, CA",
        url="https://www.linkedin.com/jobs/view/1/",
        status=JobStatus.REJECTED,
        reject_reason="not Easy Apply; estimated base below target: 180000",
    )

    assert should_run_llm(job) is False
    assert preview_confidence(job) == "high"


def test_should_run_llm_keeps_non_cheap_rejects_available():
    job = Job(
        job_id="1",
        title="Software Engineer",
        company="Example",
        location="Mountain View, CA",
        url="https://www.linkedin.com/jobs/view/1/",
        status=JobStatus.REJECTED,
        reject_reason="hard YOE appears too high: 8+",
    )

    assert should_run_llm(job) is True


def test_to_tsv_row_quotes_tabs_safely():
    job = Job(
        job_id="1",
        title="Software Engineer",
        company="Example",
        location="Mountain View, CA",
        url="https://www.linkedin.com/jobs/view/1/",
        status=JobStatus.NEEDS_REVIEW,
        estimated_tc=225000,
        fit_notes="matches software engineer",
    )

    assert to_tsv_row(job) == (
        "Software Engineer\tExample\tMountain View, CA\tneeds_review\t$225,000\t"
        "matches software engineer\thttps://www.linkedin.com/jobs/view/1/"
    )


def test_print_llm_judgment_is_consolidated(capsys):
    print_llm_judgment(LlmJudgment(
        decision="needs_review",
        confidence="high",
        role_family="backend",
        reason="Required qualifications align with backend role.",
    ))

    output = capsys.readouterr().out
    assert "Decision: needs_review" in output
    assert "Confidence: high" in output
    assert "Role family: backend" in output
    assert "Reason: Required qualifications align with backend role." in output
    assert "Hard gaps:" not in output
    assert "Required skills:" not in output
