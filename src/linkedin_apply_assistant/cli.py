from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

from .applicant import load_applicant_profile, resolve_resume_path
from .criteria import classify_job, load_criteria
from .context_rules import load_context_rules
from .job_sections import section_headers, section_text, split_job_sections
from .llm_judge import LlmJudgment, build_judge_payload, judge_job_with_llm
from .linkedin_apply import ApplyResult, fill_linkedin_easy_apply
from .linkedin_search import extract_job_from_url, extract_jobs_from_page, open_login_session
from .models import Job, JobStatus
from .search_url import build_linkedin_search_url, load_search_presets
from .storage import connect, export_jobs, upsert_jobs


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "data" / "jobs.sqlite"
DEFAULT_CRITERIA = ROOT / "config" / "criteria.yaml"
DEFAULT_CONTEXT_RULES = ROOT / "config" / "context_rules.yaml"
DEFAULT_SEARCHES = ROOT / "config" / "searches.yaml"
DEFAULT_PROFILE = ROOT / "data" / "browser-profile"
DEFAULT_APPLICANT = ROOT / "config" / "applicant.yaml"
DEFAULT_RESUME_ROOT = Path("/Users/jbgarner/Documents/resume/role_families")


def main() -> None:
    parser = argparse.ArgumentParser(prog="jobbot")
    sub = parser.add_subparsers(dest="cmd", required=True)

    discover = sub.add_parser("discover", help="Scrape visible LinkedIn search result cards.")
    discover.add_argument("--search-url")
    discover.add_argument("--preset")
    discover.add_argument("--searches", type=Path, default=DEFAULT_SEARCHES)
    discover.add_argument("--criteria", type=Path, default=DEFAULT_CRITERIA)
    discover.add_argument("--context-rules", type=Path, default=DEFAULT_CONTEXT_RULES)
    discover.add_argument("--db", type=Path, default=DEFAULT_DB)
    discover.add_argument("--profile-dir", type=Path, default=DEFAULT_PROFILE)
    discover.add_argument("--headful", action="store_true")
    discover.add_argument("--keep-open", action="store_true")
    discover.add_argument("--max-scrolls", type=int, default=5)
    discover.add_argument("--limit", type=int, default=5, help="Number of hydrated postings to review before DB approval.")

    login = sub.add_parser("login", help="Open LinkedIn and keep the browser open for manual login.")
    login.add_argument("--profile-dir", type=Path, default=DEFAULT_PROFILE)
    login.add_argument("--url", default="https://www.linkedin.com/jobs/")

    preview = sub.add_parser("preview", help="Classify one LinkedIn job URL without writing to SQLite.")
    preview.add_argument("--job-url", required=True)
    preview.add_argument("--criteria", type=Path, default=DEFAULT_CRITERIA)
    preview.add_argument("--context-rules", type=Path, default=DEFAULT_CONTEXT_RULES)
    preview.add_argument("--profile-dir", type=Path, default=DEFAULT_PROFILE)
    preview.add_argument("--headful", action="store_true")
    preview.add_argument("--debug-sections", action="store_true", help="Print extracted metadata and job sections before rule checks.")
    preview.add_argument("--llm-rules", action="store_true", help="Print an advisory LLM required/preferred gap check.")
    preview.add_argument("--force-llm", action="store_true", help="Run --llm-rules even when cheap deterministic filters reject the job.")
    preview.add_argument("--debug-llm", action="store_true", help="Print exact LLM request JSON and raw response without headers or API key.")
    preview.add_argument("--llm-model", default=None, help="Override OPENAI_MODEL for --llm-rules.")

    export = sub.add_parser("export", help="Export queued jobs as TSV.")
    export.add_argument("--db", type=Path, default=DEFAULT_DB)
    export.add_argument("--status", default=None)
    export.add_argument("--format", choices=["pretty", "tsv"], default="pretty")

    apply = sub.add_parser("apply", help="Fill LinkedIn Easy Apply and pause before final submit.")
    apply.add_argument("--job-url", required=True)
    apply.add_argument("--resume-family", required=True)
    apply.add_argument("--applicant", type=Path, default=DEFAULT_APPLICANT)
    apply.add_argument("--resume-root", type=Path, default=DEFAULT_RESUME_ROOT)
    apply.add_argument("--profile-dir", type=Path, default=DEFAULT_PROFILE)
    apply.add_argument("--headless", action="store_true")
    apply.add_argument("--close-when-done", action="store_true")

    args = parser.parse_args()
    if args.cmd == "discover":
        run_discover(args)
    elif args.cmd == "login":
        run_login(args)
    elif args.cmd == "preview":
        run_preview(args)
    elif args.cmd == "export":
        run_export(args)
    elif args.cmd == "apply":
        run_apply(args)


def run_discover(args: argparse.Namespace) -> None:
    criteria = load_criteria(args.criteria)
    context_rules = load_context_rules(args.context_rules)
    search_url, metadata = resolve_search(args)
    jobs = extract_jobs_from_page(
        search_url=search_url,
        profile_dir=args.profile_dir,
        headful=args.headful,
        max_scrolls=args.max_scrolls,
        max_jobs=args.limit,
        keep_open=args.keep_open,
    )
    for job in jobs:
        job.search_preset = metadata["search_preset"]
    jobs = [classify_job(job, criteria, context_rules=context_rules) for job in jobs]

    needs_review = sum(1 for job in jobs if job.status.value == "needs_review")
    rejected = sum(1 for job in jobs if job.status.value == "rejected")
    print(f"discovered={len(jobs)} needs_review={needs_review} rejected={rejected}")

    approved_jobs = review_jobs_for_commit(jobs)
    if not approved_jobs:
        print("committed=0")
        return

    conn = connect(args.db)
    upsert_jobs(conn, approved_jobs)
    print(f"committed={len(approved_jobs)}")


def run_export(args: argparse.Namespace) -> None:
    conn = connect(args.db)
    rows = export_jobs(conn, args.status)
    if args.format == "pretty":
        print_pretty_export(rows)
        return

    writer = csv.writer(sys.stdout, delimiter="\t", lineterminator="\n")
    writer.writerow([
        "status",
        "score",
        "search_preset",
        "title",
        "company",
        "location",
        "salary_text",
        "estimated_base",
        "reason",
        "url",
    ])
    for row in rows:
        estimated_base = ""
        if row["estimated_tc"]:
            estimated_base = f"${row['estimated_tc']:,}"
        writer.writerow(
            [
                row["status"],
                row["score"],
                row["search_preset"],
                row["title"],
                row["company"],
                row["location"],
                row["salary_text"],
                estimated_base,
                row["reject_reason"] or row["fit_notes"],
                row["url"],
            ]
        )


def run_preview(args: argparse.Namespace) -> None:
    criteria = load_criteria(args.criteria)
    context_rules = load_context_rules(args.context_rules)
    job = extract_job_from_url(
        job_url=args.job_url,
        profile_dir=args.profile_dir,
        headful=args.headful,
    )
    if args.debug_sections:
        print_section_debug(job)
        print()
    job = classify_job(job, criteria, context_rules=context_rules)
    print_preview_report(job)
    if args.llm_rules:
        print()
        if args.force_llm or should_run_llm(job):
            try:
                print_llm_judgment(judge_job_with_llm(job, model=args.llm_model, debug=args.debug_llm))
            except RuntimeError as exc:
                print(f"LLM rule check skipped: {exc}")
        else:
            print(f"LLM rule check skipped: cheap deterministic reject ({job.reject_reason}).")


def print_pretty_export(rows) -> None:
    if not rows:
        print("No jobs found.")
        return

    widths = {
        "status": 12,
        "score": 5,
        "preset": 18,
        "title": 46,
        "company": 28,
        "location": 50,
        "base": 10,
        "why": 64,
    }
    print(_format_row(["status", "score", "preset", "title", "company", "location", "base", "why", "url"], widths))
    print(_format_row(["-" * widths["status"], "-" * widths["score"], "-" * widths["preset"], "-" * widths["title"], "-" * widths["company"], "-" * widths["location"], "-" * widths["base"], "-" * widths["why"], "---"], widths))
    for idx, row in enumerate(rows, start=1):
        estimated_base = ""
        if row["estimated_tc"]:
            estimated_base = f"${row['estimated_tc']:,}"
        reason = row["reject_reason"] or row["fit_notes"] or "-"
        print(_format_row(
            [
                row["status"],
                str(row["score"]),
                row["search_preset"] or "-",
                row["title"],
                row["company"],
                row["location"],
                estimated_base or "-",
                reason,
                row["url"],
            ],
            widths,
        )
        )


def print_pretty_job(job) -> None:
    estimated_base = ""
    if job.estimated_tc:
        estimated_base = f"${job.estimated_tc:,}"
    reason = job.reject_reason or job.fit_notes or "-"
    print(f"{job.title} — {job.company}")
    print(f"Status: {job.status.value} | Score: {job.score} | Preset: {job.search_preset or '-'}")
    work_mode = f" ({job.work_mode})" if job.work_mode else ""
    print(f"Location: {_truncate(job.location + work_mode, 50)}")
    if job.salary_text or estimated_base:
        print(f"Pay: {job.salary_text or '-'} | Est base: {estimated_base or '-'}")
    print(f"Why: {reason}")
    if job.reject_reason and job.fit_notes:
        print(f"Notes: {job.fit_notes}")
    print(f"URL: {job.url}")


def print_preview_report(job: Job) -> None:
    estimated_base = f"${job.estimated_tc:,}" if job.estimated_tc else "-"
    reason = job.reject_reason or job.fit_notes or "-"
    confidence = preview_confidence(job)
    work_mode = f" ({job.work_mode})" if job.work_mode else ""

    print(f"Title: {job.title}")
    print(f"Company: {job.company}")
    print(f"Location: {_truncate(job.location + work_mode, 80)}")
    print(f"Base: {estimated_base}")
    print(f"Easy Apply: {job.easy_apply}")
    print(f"Decision: {job.status.value}")
    print(f"Confidence: {confidence}")
    print(f"Why: {reason}")

    evidence = preview_evidence(job)
    if evidence:
        print("Evidence:")
        for item in evidence:
            print(f"- {item}")

    print_section_summary(job)
    print("TSV:")
    print(to_tsv_row(job))
    print(f"URL: {job.url}")


def preview_confidence(job: Job) -> str:
    if job.status == JobStatus.NEEDS_REVIEW:
        return "medium"
    reason = job.reject_reason.lower()
    if any(term in reason for term in ["not easy apply", "location outside", "estimated base below", "role mismatch", "hard yoe"]):
        return "high"
    return "medium"


def preview_evidence(job: Job) -> list[str]:
    evidence: list[str] = []
    reason = job.reject_reason.lower()
    if "not easy apply" in reason:
        evidence.append("Easy Apply signal was not found on the detail/search page.")
    if "location outside" in reason:
        evidence.append(f"Extracted location: {job.location or '-'}; work mode: {job.work_mode or '-'}.")
    if "estimated base below" in reason:
        evidence.append(f"Extracted salary text: {job.salary_text or '-'}; estimated base: ${job.estimated_tc:,}.")
    if "hard yoe" in reason:
        evidence.append("Required/qualification section contains a years-of-experience minimum above the configured maximum.")
    if "role mismatch" in reason:
        evidence.append(f"Extracted title/company: {job.title} — {job.company}.")
    return evidence


def print_section_summary(job: Job) -> None:
    sections = split_job_sections(job.description)
    required_headers = section_headers(sections, {"required", "qualifications"})
    preferred_headers = section_headers(sections, {"preferred"})
    required_text = _truncate(section_text(sections, {"required", "qualifications"}), 280) or "-"
    preferred_text = _truncate(section_text(sections, {"preferred"}), 220) or "-"
    print("Required sections:")
    print(f"- Headers: {', '.join(required_headers) if required_headers else '-'}")
    print(f"- Body: {required_text}")
    print("Preferred sections:")
    print(f"- Headers: {', '.join(preferred_headers) if preferred_headers else '-'}")
    print(f"- Body: {preferred_text}")


def to_tsv_row(job: Job) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter="\t", lineterminator="")
    writer.writerow([
        job.title,
        job.company,
        job.location,
        job.status.value,
        f"${job.estimated_tc:,}" if job.estimated_tc else "",
        job.reject_reason or job.fit_notes,
        job.url,
    ])
    return buffer.getvalue()


def should_run_llm(job: Job) -> bool:
    if job.status == JobStatus.NEEDS_REVIEW:
        return True
    reason = job.reject_reason.lower()
    cheap_rejects = ["not easy apply", "location outside", "estimated base below", "role mismatch"]
    return not any(term in reason for term in cheap_rejects)


def review_jobs_for_commit(jobs, input_fn=input) -> list:
    approved = []
    total = len(jobs)
    for idx, job in enumerate(jobs, start=1):
        print()
        print(f"[{idx}/{total}]")
        print_pretty_job(job)
        while True:
            answer = input_fn("Commit to DB? [y/N/q] ").strip().lower()
            if answer in {"", "n", "no", "d", "discard"}:
                break
            if answer in {"y", "yes", "c", "commit"}:
                approved.append(job)
                break
            if answer in {"q", "quit"}:
                return approved
            print("Please enter y, n, or q.")
    return approved


def print_llm_judgment(judgment: LlmJudgment) -> None:
    print("LLM rule check:")
    print(f"Decision: {judgment.decision}")
    print(f"Confidence: {judgment.confidence}")
    if judgment.role_family:
        print(f"Role family: {judgment.role_family}")
    if judgment.reason:
        print(f"Reason: {judgment.reason}")


def print_section_debug(job) -> None:
    payload = build_judge_payload(job)
    sections = split_job_sections(job.description)
    print("Extracted payload:")
    print(f"Title: {payload['title']}")
    print(f"Company: {payload['company']}")
    print(f"Location: {payload['location']}")
    print(f"Work mode: {payload['work_mode'] or '-'}")
    print(f"Salary: {payload['salary_text'] or '-'}")
    print(f"Easy Apply: {payload['easy_apply']}")
    print(f"LLM required sections: {len(payload['required_sections'])}")
    print("Sections:")
    for idx, section in enumerate(sections, start=1):
        body = _truncate(section.text, 600)
        print(f"[{idx}] {section.kind} | {section.header or 'Overview'}")
        print(f"    {body}")


def _truncate(value: str, max_chars: int) -> str:
    text = str(value or "")
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def _format_row(values: list[str], widths: dict[str, int]) -> str:
    keys = ["status", "score", "preset", "title", "company", "location", "base", "why"]
    cells = [
        _truncate(str(value), widths[key]).ljust(widths[key])
        for key, value in zip(keys, values[: len(keys)])
    ]
    return "  ".join(cells + [str(values[-1])])


def run_login(args: argparse.Namespace) -> None:
    open_login_session(profile_dir=args.profile_dir, url=args.url)


def run_apply(args: argparse.Namespace) -> None:
    applicant = load_applicant_profile(args.applicant)
    resume_path = resolve_resume_path(args.resume_root, args.resume_family)
    result = fill_linkedin_easy_apply(
        job_url=args.job_url,
        profile_dir=args.profile_dir,
        resume_path=resume_path,
        applicant=applicant,
        headless=args.headless,
        keep_open=not args.close_when_done,
    )
    print_apply_result(result)


def print_apply_result(result: ApplyResult) -> None:
    print("Apply fill result:")
    print(f"URL: {result.job_url}")
    print(f"Resume: {result.resume_path}")
    print(f"Reached submit review: {result.reached_submit_review}")
    if result.step_history:
        print(f"Steps seen: {' -> '.join(result.step_history)}")
    if result.filled_fields:
        print("Filled:")
        for field in result.filled_fields:
            print(f"- {field}")
    if result.unknown_required_fields:
        print("Unknown required fields:")
        for field in result.unknown_required_fields:
            print(f"- {field}")
    if result.blockers:
        print("Blockers:")
        for blocker in result.blockers:
            print(f"- {blocker}")
    if result.kept_open:
        print("Browser was kept open for manual review before closing.")
    print("No final submit was clicked.")


def resolve_search(args: argparse.Namespace) -> tuple[str, dict[str, str]]:
    if args.search_url and args.preset:
        raise SystemExit("Use either --search-url or --preset, not both.")
    if args.search_url:
        return args.search_url, {
            "search_preset": "",
        }
    if not args.preset:
        raise SystemExit("Provide --search-url or --preset.")

    presets = load_search_presets(args.searches)
    if args.preset not in presets:
        allowed = ", ".join(sorted(presets))
        raise SystemExit(f"Unknown preset {args.preset!r}; allowed: {allowed}")
    preset = presets[args.preset]
    return build_linkedin_search_url(preset), {"search_preset": args.preset}


if __name__ == "__main__":
    main()
