from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from typing import Iterable

from .models import Job


LINKEDIN_JOB_ID_RE = re.compile(r"(?:currentJobId=|/jobs/view/)(\d+)")
LINKEDIN_DASH_RE = r"[-–—]"
MONEY_SUFFIX_BOUNDARY = r"(?![\dA-Za-z])(?!(?:\s*(?:[mM]\b|million|billion)))"
MAX_LOCATION_CHARS = 50


def normalize_job_url(url: str) -> str:
    match = LINKEDIN_JOB_ID_RE.search(url or "")
    if not match:
        return url
    return f"https://www.linkedin.com/jobs/view/{match.group(1)}/"


def job_id_from_url(url: str) -> str:
    match = LINKEDIN_JOB_ID_RE.search(url or "")
    return match.group(1) if match else url


def extract_jobs_from_page(
    search_url: str,
    profile_dir: Path,
    headful: bool,
    max_scrolls: int,
    max_jobs: int = 5,
    keep_open: bool = False,
) -> list[Job]:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=not headful,
            viewport={"width": 1440, "height": 1000},
        )
        page = context.new_page()
        page.goto(search_url, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_timeout(2500)

        for _ in range(max_scrolls):
            page.mouse.wheel(0, 1400)
            page.wait_for_timeout(700)

        raw_jobs = page.evaluate(
            """
            () => {
              const selectors = [
                'li.jobs-search-results__list-item',
                '.job-card-container',
                '[data-job-id]'
              ];
              const cards = Array.from(new Set(selectors.flatMap(s => Array.from(document.querySelectorAll(s)))));
              const jobs = cards.slice(0, 250).map(card => {
                const text = (card.innerText || card.textContent || '').replace(/\\s+/g, ' ').trim();
                const link = card.querySelector('a[href*="/jobs/view/"]');
                const href = link ? link.href : '';
                const title =
                  card.querySelector('.job-card-list__title--link strong')?.innerText ||
                  card.querySelector('.job-card-list__title')?.innerText ||
                  card.querySelector('a[href*="/jobs/view/"] strong')?.innerText ||
                  card.querySelector('a[href*="/jobs/view/"]')?.innerText ||
                  '';
                const company =
                  card.querySelector('.artdeco-entity-lockup__subtitle')?.innerText ||
                  card.querySelector('.job-card-container__primary-description')?.innerText ||
                  '';
                const location =
                  card.querySelector('.artdeco-entity-lockup__caption')?.innerText ||
                  card.querySelector('.job-card-container__metadata-item')?.innerText ||
                  '';
                return { text, href, title, company, location };
              }).filter(j => j.href || j.title);
              if (jobs.length) return jobs;

              const seen = new Set();
              return Array.from(document.querySelectorAll('a[href*="/jobs/view/"]'))
                .map(link => {
                  const href = link.href || '';
                  const idMatch = href.match(/\\/jobs\\/view\\/(\\d+)/);
                  const key = idMatch ? idMatch[1] : href;
                  if (!key || seen.has(key)) return null;
                  seen.add(key);
                  return {
                    text: (link.innerText || link.textContent || '').replace(/\\s+/g, ' ').trim(),
                    href,
                    title: (link.innerText || link.textContent || '').replace(/\\s+/g, ' ').trim(),
                    company: '',
                    location: ''
                  };
                })
                .filter(Boolean)
                .slice(0, 250);
            }
            """
        )
        if len(raw_jobs) <= 1:
            raw_jobs = _merge_raw_jobs(raw_jobs, _collect_selected_search_results(page, max_scrolls=max_scrolls, max_jobs=max_jobs))
        raw_jobs = raw_jobs[:max_jobs]
        _hydrate_detail_text(context, raw_jobs)
        if keep_open:
            input("Discovery finished. Press Enter here to close the browser...")
        context.close()

    search_is_easy_apply = _search_has_easy_apply_filter(search_url)
    return list(_to_jobs(raw_jobs, search_is_easy_apply=search_is_easy_apply, require_detail=True))


def _collect_selected_search_results(page, max_scrolls: int, max_jobs: int) -> list[dict]:
    raw_jobs: list[dict] = []
    seen: set[str] = set()

    # LinkedIn's newer AI job-search layout may render many visible rows as
    # clickable text without stable cards, anchors, or data-job-id attributes.
    # Clicking rows updates currentJobId in the URL, which gives us a stable
    # detail-page URL to hydrate later.
    for _ in range(max(1, max_scrolls + 1)):
        for y in range(230, 970, 80):
            page.mouse.click(330, y)
            page.wait_for_timeout(900)
            job_id = _current_job_id_from_url(page.url)
            if not job_id or job_id in seen:
                continue
            seen.add(job_id)
            title = page.title().split("|", 1)[0].strip()
            raw_jobs.append(
                {
                    "href": f"https://www.linkedin.com/jobs/view/{job_id}/",
                    "title": title,
                    "company": "",
                    "location": "",
                    "text": title,
                }
            )
            if len(raw_jobs) >= max_jobs:
                return raw_jobs
        page.mouse.wheel(0, 900)
        page.wait_for_timeout(900)

    return raw_jobs


def _merge_raw_jobs(primary: list[dict], fallback: list[dict]) -> list[dict]:
    merged: list[dict] = []
    seen: set[str] = set()
    for raw in primary + fallback:
        job_id = job_id_from_url(raw.get("href", ""))
        if not job_id or job_id in seen:
            continue
        seen.add(job_id)
        merged.append(raw)
    return merged


def _current_job_id_from_url(url: str) -> str:
    query = parse_qs(urlparse(url).query)
    if query.get("currentJobId"):
        return query["currentJobId"][0]
    return job_id_from_url(url)


def extract_job_from_url(job_url: str, profile_dir: Path, headful: bool) -> Job:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=not headful,
            viewport={"width": 1440, "height": 1000},
        )
        page = context.new_page()
        page.goto(normalize_job_url(job_url), wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_timeout(2500)
        raw_job = page.evaluate(
            """
            () => {
              const text = (document.body.innerText || document.body.textContent || '').replace(/\\s+/g, ' ').trim();
              const descriptionNode =
                document.querySelector('.jobs-description') ||
                document.querySelector('.jobs-box__html-content');
              let descriptionText = ((descriptionNode && (descriptionNode.innerText || descriptionNode.textContent)) || '').replace(/\\s+/g, ' ').trim();
              if (!descriptionText) {
                const aboutIndex = text.indexOf('About the job');
                const companyIndex = text.indexOf('About the company');
                if (aboutIndex >= 0) {
                  const endIndex = companyIndex > aboutIndex ? companyIndex : text.length;
                  descriptionText = text.slice(aboutIndex, endIndex).trim();
                }
              }
              const applyText = Array.from(document.querySelectorAll('button, a'))
                .map((el) => [
                  el.innerText || el.textContent || '',
                  el.getAttribute('aria-label') || '',
                  el.href || ''
                ].join(' '))
                .join(' ');
              const title =
                document.querySelector('.job-details-jobs-unified-top-card__job-title h1')?.innerText ||
                document.querySelector('.jobs-unified-top-card__job-title')?.innerText ||
                document.querySelector('h1')?.innerText ||
                document.title ||
                '';
              const company =
                document.querySelector('.job-details-jobs-unified-top-card__company-name')?.innerText ||
                document.querySelector('.jobs-unified-top-card__company-name')?.innerText ||
                '';
              const locationText =
                document.querySelector('.job-details-jobs-unified-top-card__primary-description-container')?.innerText ||
                document.querySelector('.jobs-unified-top-card__bullet')?.innerText ||
                '';
              const topCardText = (
                document.querySelector('.job-details-jobs-unified-top-card')?.innerText ||
                document.querySelector('.jobs-unified-top-card')?.innerText ||
                locationText ||
                ''
              ).replace(/\\s+/g, ' ').trim();
              return { text: `${topCardText} ${descriptionText || ''} ${applyText}`, top_card_text: topCardText, detail_text: descriptionText, page_text: text, href: window.location.href, title, company, location: locationText };
            }
            """
        )
        _clean_single_job(raw_job)
        context.close()

    jobs = list(_to_jobs([raw_job], search_is_easy_apply=False))
    if not jobs:
        raise RuntimeError(f"Could not extract job from URL: {job_url}")
    return jobs[0]


def _clean_single_job(raw_job: dict) -> None:
    title = (raw_job.get("title") or "").strip()
    company = (raw_job.get("company") or "").strip()
    text = raw_job.get("detail_text") or raw_job.get("text") or ""
    page_text = raw_job.get("page_text") or text
    top_card_text = raw_job.get("top_card_text") or ""

    # Public/logged-in LinkedIn pages sometimes expose the best title/company
    # only through document.title, e.g. "Role | Company | LinkedIn".
    title_parts = [part.strip() for part in title.split("|")]
    if len(title_parts) >= 2 and title_parts[-1].lower() == "linkedin":
        raw_job["title"] = title_parts[0]
        if not company:
            raw_job["company"] = title_parts[1]
    top_card_text = top_card_text or _top_card_from_page_text(raw_job.get("title") or "", page_text)

    location = (raw_job.get("location") or "").strip()
    if "·" in location:
        location = location.split("·", 1)[0].strip()
    location = _clean_location_text(location)
    detail_location = _location_from_detail_text(text)
    header_location = _location_from_page_header(raw_job.get("title") or "", top_card_text or page_text)
    if detail_location or header_location:
        location = detail_location or header_location
    if not location:
        location_match = re.search(r"\|\s*([^|·]+?)\s*\|\s*\d+\s*[–\-]\s*\d+\s*years", text, re.I)
        if not location_match:
            location_match = re.search(r"\b((?:San Francisco|San Fransisco|Mountain View|Palo Alto|Sunnyvale|Santa Clara|Menlo Park|Redwood City|San Mateo)[^·|]*)\s*[·|]", text)
        if not location_match:
            location_match = re.search(r"\b((?:San Francisco|San Fransisco|Mountain View|Palo Alto|Sunnyvale|Santa Clara|Menlo Park|Redwood City|San Mateo)[^·|]*)\s*[·|]", page_text)
        if location_match:
            location = location_match.group(1).strip()
    raw_job["location"] = _normalize_location(location)
    raw_job["detail_text"] = _strip_linkedin_noise(raw_job.get("detail_text") or "")
    raw_job["work_mode"] = _work_mode_from_text(top_card_text) or _work_mode_from_text(raw_job["detail_text"])


def _clean_location_text(location: str) -> str:
    cleaned = (location or "").strip()
    for marker in ["You’d be", "You'd be", "Promoted"]:
        if marker in cleaned:
            cleaned = cleaned.split(marker, 1)[0].strip()
    return cleaned


def _normalize_location(location: str) -> str:
    return _truncate_location(_clean_location_text(location).replace("San Fransisco", "San Francisco"))


def _truncate_location(location: str) -> str:
    text = (location or "").strip()
    if len(text) <= MAX_LOCATION_CHARS:
        return text
    return text[: MAX_LOCATION_CHARS - 1].rstrip() + "…"


def _location_from_page_header(title: str, page_text: str) -> str:
    if not title or not page_text:
        return ""

    compact = re.sub(r"\s+", " ", page_text).strip()
    title_idx = compact.find(title.strip())
    if title_idx < 0:
        return ""

    # In the logged-in job view, LinkedIn often renders:
    # "<title> San Jose, CA · 6 days ago · Over 100 applicants ..."
    after_title = compact[title_idx + len(title.strip()) : title_idx + len(title.strip()) + 220]
    location_match = re.search(
        r"\b((?:San Jose|San Francisco|Mountain View|Palo Alto|Sunnyvale|Santa Clara|Menlo Park|Redwood City|San Mateo)[^·|]*)\s*[·|]",
        after_title,
    )
    if location_match:
        return _clean_location_text(location_match.group(1).strip())
    return ""


def _top_card_from_page_text(title: str, page_text: str) -> str:
    if not title or not page_text:
        return ""

    compact = re.sub(r"\s+", " ", page_text).strip()
    title_idx = compact.find(title.strip())
    if title_idx < 0:
        return ""

    about_idx = compact.find("About the job", title_idx)
    if about_idx < 0:
        about_idx = title_idx + 500
    return compact[title_idx:min(about_idx, title_idx + 700)].strip()


def _location_from_detail_text(text: str) -> str:
    match = re.search(
        r"\bLocation\s*(?:&\s*Package)?\s*:?\s*(?:📍\s*)?"
        r"((?:San Jose|San Francisco|Mountain View|Palo Alto|Sunnyvale|Santa Clara|Menlo Park|Redwood City|San Mateo)[^·|\n]*?)"
        r"(?=\s*(?:🏠|•|·|…|About|Company Stage|Office Type|Salary|Company Description|Working Model|Work Model|$))",
        text or "",
        re.I,
    )
    return _clean_location_text(match.group(1).strip()) if match else ""


def _work_mode_from_text(text: str) -> str:
    lower = (text or "").lower()
    if "hybrid" in lower:
        return "Hybrid"
    if "on-site" in lower or "onsite" in lower:
        return "On-site"
    if "remote" in lower:
        return "Remote"
    return ""


def _strip_linkedin_noise(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    for marker in [
        "Set alert for similar jobs",
        "See how you compare to other applicants",
        "Exclusive Job Seeker Insights",
        "Powered by Bing",
        "More jobs",
        "Show Premium Insights",
        "Looking for talent?",
    ]:
        idx = cleaned.find(marker)
        if idx >= 0:
            return cleaned[:idx].strip()
    return cleaned


def _hydrate_detail_text(context, raw_jobs: list[dict]) -> None:
    detail_page = context.new_page()
    try:
        for raw in raw_jobs:
            href = raw.get("href", "")
            if not href:
                continue
            try:
                detail_page.goto(normalize_job_url(href), wait_until="domcontentloaded", timeout=30_000)
                detail_page.wait_for_timeout(900)
                detail_data = detail_page.evaluate(
                    """
                    () => {
                      const text = (document.body.innerText || document.body.textContent || '').replace(/\\s+/g, ' ').trim();
                      const node =
                        document.querySelector('.jobs-description') ||
                        document.querySelector('.jobs-box__html-content');
                      let detailText = ((node && (node.innerText || node.textContent)) || '').replace(/\\s+/g, ' ').trim();
                      if (!detailText) {
                        const aboutIndex = text.indexOf('About the job');
                        const companyIndex = text.indexOf('About the company');
                        if (aboutIndex >= 0) {
                          const endIndex = companyIndex > aboutIndex ? companyIndex : text.length;
                          detailText = text.slice(aboutIndex, endIndex).trim();
                        }
                      }
                      const title =
                        document.querySelector('.job-details-jobs-unified-top-card__job-title h1')?.innerText ||
                        document.querySelector('.jobs-unified-top-card__job-title')?.innerText ||
                        document.querySelector('h1')?.innerText ||
                        document.title ||
                        '';
                      const company =
                        document.querySelector('.job-details-jobs-unified-top-card__company-name')?.innerText ||
                        document.querySelector('.jobs-unified-top-card__company-name')?.innerText ||
                        '';
                      const location =
                        document.querySelector('.job-details-jobs-unified-top-card__primary-description-container')?.innerText ||
                        document.querySelector('.jobs-unified-top-card__bullet')?.innerText ||
                        '';
                      const topCardText = (
                        document.querySelector('.job-details-jobs-unified-top-card')?.innerText ||
                        document.querySelector('.jobs-unified-top-card')?.innerText ||
                        location ||
                        ''
                      ).replace(/\\s+/g, ' ').trim();
                      return { detail_text: detailText, page_text: text, top_card_text: topCardText, title, company, location };
                    }
                    """
                )
                if detail_data.get("detail_text"):
                    raw.update({key: value for key, value in detail_data.items() if value})
                    raw["detail_text"] = _strip_linkedin_noise(raw.get("detail_text", ""))
                    _clean_single_job(raw)
            except Exception as exc:
                raw["detail_error"] = str(exc)
    finally:
        detail_page.close()


def open_login_session(profile_dir: Path, url: str) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
            viewport={"width": 1440, "height": 1000},
        )
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        input("Log in or verify the session in the browser, then press Enter here to close and save it...")
        context.close()


def _to_jobs(raw_jobs: Iterable[dict], search_is_easy_apply: bool = False, require_detail: bool = False) -> Iterable[Job]:
    seen: set[str] = set()
    for raw in raw_jobs:
        url = normalize_job_url(raw.get("href", ""))
        job_id = job_id_from_url(url)
        if not job_id or job_id in seen:
            continue
        seen.add(job_id)
        card_text = raw.get("text", "")
        detail_text = _strip_linkedin_noise(raw.get("detail_text", ""))
        if require_detail and not detail_text:
            continue
        signal_text = " ".join(part for part in [card_text, detail_text] if part)
        description = detail_text or card_text
        yield Job(
            job_id=job_id,
            title=(raw.get("title") or "").strip(),
            company=(raw.get("company") or "").strip(),
            location=_normalize_location(raw.get("location") or ""),
            url=url,
            easy_apply=search_is_easy_apply or _card_has_easy_apply_signal(signal_text),
            salary_text=_salary_from_text(signal_text),
            work_mode=raw.get("work_mode", "") or _work_mode_from_text(signal_text),
            posted_at=_posted_from_text(signal_text),
            description=description,
        )


def _search_has_easy_apply_filter(search_url: str) -> bool:
    query = parse_qs(urlparse(search_url).query)
    return any(value.lower() == "true" for value in query.get("f_AL", []))


def _card_has_easy_apply_signal(text: str) -> bool:
    lower = (text or "").lower()
    return (
        "easy apply" in lower
        or "in apply" in lower
        or "linkedin apply" in lower
        or "openSDUIApplyFlow=true".lower() in lower
    )


def _salary_from_text(text: str) -> str:
    # Keep the original card salary text compact, while supporting both
    # "$200,000-$350,000" and "$200k-$350k" style ranges.
    match = re.search(
        rf"\$\s*\d[\d,]*(?:[kK])?{MONEY_SUFFIX_BOUNDARY}(?:\s*(?:/yr|/year|a year))?(?:\s*{LINKEDIN_DASH_RE}\s*\$?\s*\d[\d,]*(?:[kK])?{MONEY_SUFFIX_BOUNDARY}(?:\s*(?:/yr|/year|a year))?)?(?:\s*(?:base))?",
        text or "",
        re.I,
    )
    return match.group(0) if match else ""


def _posted_from_text(text: str) -> str:
    match = re.search(r"\b(?:\d+\s+(?:hours?|days?|weeks?)\s+ago|Just now|Reposted)\b", text or "", re.I)
    return match.group(0) if match else ""
