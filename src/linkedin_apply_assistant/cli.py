from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from .criteria import classify_job, load_criteria
from .context_rules import load_context_rules
from .linkedin_search import extract_job_from_url, extract_jobs_from_page, open_login_session
from .search_url import build_linkedin_search_url, load_search_presets
from .storage import connect, export_jobs, upsert_jobs


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "data" / "jobs.sqlite"
DEFAULT_CRITERIA = ROOT / "config" / "criteria.yaml"
DEFAULT_CONTEXT_RULES = ROOT / "config" / "context_rules.yaml"
DEFAULT_SEARCHES = ROOT / "config" / "searches.yaml"
DEFAULT_PROFILE = ROOT / "data" / "browser-profile"


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

    export = sub.add_parser("export", help="Export queued jobs as TSV.")
    export.add_argument("--db", type=Path, default=DEFAULT_DB)
    export.add_argument("--status", default=None)
    export.add_argument("--format", choices=["pretty", "tsv"], default="pretty")

    args = parser.parse_args()
    if args.cmd == "discover":
        run_discover(args)
    elif args.cmd == "login":
        run_login(args)
    elif args.cmd == "preview":
        run_preview(args)
    elif args.cmd == "export":
        run_export(args)


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
    job = classify_job(job, criteria, context_rules=context_rules)
    print_pretty_job(job)


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
