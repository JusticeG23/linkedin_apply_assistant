from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .applicant import ApplicantProfile, answer_for_label
from .linkedin_search import normalize_job_url


FIELD_LABEL_JS = """
(el) => {
  function clean(value) {
    return (value || '').replace(/\\s+/g, ' ').trim();
  }
  const parts = [];
  for (const attr of ['aria-label', 'placeholder', 'name', 'id']) {
    const value = clean(el.getAttribute(attr));
    if (value) parts.push(value);
  }
  if (el.id) {
    const label = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
    if (label) parts.push(clean(label.innerText || label.textContent));
  }
  const wrappingLabel = el.closest('label');
  if (wrappingLabel) parts.push(clean(wrappingLabel.innerText || wrappingLabel.textContent));
  const container = el.closest('.jobs-easy-apply-form-section__grouping, .fb-dash-form-element, .artdeco-text-input--container');
  if (container) {
    const text = clean(container.innerText || container.textContent);
    if (text && text.length <= 180) parts.push(text);
  }
  return Array.from(new Set(parts.filter(Boolean))).join(' | ');
}
"""


REQUIRED_JS = """
(el) => {
  if (el.required || el.getAttribute('aria-required') === 'true') return true;
  const text = (el.closest('.jobs-easy-apply-form-section__grouping, .fb-dash-form-element, div')?.innerText || '').toLowerCase();
  return text.includes('required') || text.includes('*');
}
"""


@dataclass
class ApplyResult:
    job_url: str
    resume_path: Path
    filled_fields: list[str] = field(default_factory=list)
    unknown_required_fields: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    step_history: list[str] = field(default_factory=list)
    reached_submit_review: bool = False
    kept_open: bool = False


def fill_linkedin_easy_apply(
    job_url: str,
    profile_dir: Path,
    resume_path: Path,
    applicant: ApplicantProfile,
    *,
    headless: bool = False,
    keep_open: bool = True,
) -> ApplyResult:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright

    result = ApplyResult(job_url=normalize_job_url(job_url), resume_path=resume_path)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=headless,
            viewport={"width": 1440, "height": 1000},
        )
        page = context.new_page()
        try:
            page.goto(result.job_url, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(2500)
            if not _click_easy_apply(page, result):
                labels = _visible_clickable_labels(page)
                suffix = f" Visible buttons/links: {', '.join(labels[:12])}" if labels else ""
                result.blockers.append(f"Easy Apply button not found on the canonical job page.{suffix}")
                return result

            page.wait_for_timeout(1500)

            for _ in range(8):
                modal = _application_modal(page)
                step = _detect_step(modal)
                result.step_history.append(step)

                if step == "review":
                    result.reached_submit_review = True
                    break
                if step == "resume":
                    _upload_resume_if_possible(modal, resume_path, result)
                else:
                    _fill_visible_fields(modal, applicant, result)

                required_unknowns = _unknown_required_fields(modal, applicant)
                for label in required_unknowns:
                    if label not in result.unknown_required_fields:
                        result.unknown_required_fields.append(label)

                submit_button = _find_step_button(modal, {"submit application"})
                if submit_button:
                    result.reached_submit_review = True
                    break
                if result.unknown_required_fields:
                    labels = _visible_clickable_labels(modal)
                    if labels:
                        result.blockers.append(f"Stopped before next because unknown required fields remain. Visible modal buttons: {', '.join(labels[:8])}")
                    break

                next_button = _find_step_button(modal, {"next", "continue", "review"})
                if not next_button:
                    result.reached_submit_review = bool(_find_step_button(modal, {"submit application"}))
                    if not result.reached_submit_review:
                        labels = _visible_clickable_labels(modal)
                        suffix = f" Visible modal buttons: {', '.join(labels[:8])}" if labels else ""
                        result.blockers.append(f"No Next/Review/Submit button found after filling visible fields.{suffix}")
                    break
                try:
                    label = _clickable_label(next_button)
                    if not _click_candidate(next_button):
                        result.blockers.append(f"Could not click the next/review button: {_compact_label(label)}")
                        break
                    result.filled_fields.append(f"clicked: {_compact_label(label or 'next step')}")
                    page.wait_for_timeout(1200)
                except PlaywrightTimeoutError:
                    result.blockers.append("Could not click the next/review button.")
                    break
        finally:
            _finish(context, result, keep_open)

    return result


def _finish(context, result: ApplyResult, keep_open: bool) -> ApplyResult:
    if keep_open:
        result.kept_open = True
        input("Review the LinkedIn application in the browser. Press Enter here to close it...")
    context.close()
    return result


def _click_easy_apply(page, result: ApplyResult) -> bool:
    for _ in range(12):
        candidate = _find_easy_apply_button(page)
        if candidate:
            label = _clickable_label(candidate)
            if _click_candidate(candidate):
                result.filled_fields.append(f"clicked: {_compact_label(label or 'Easy Apply')}")
                return True
        page.wait_for_timeout(1000)
    return False


def _find_easy_apply_button(page):
    locators = [
        page.get_by_role("button", name=re.compile(r"Easy Apply|LinkedIn Apply|Apply now", re.I)),
        page.locator("button[aria-label*='Easy Apply'], button[aria-label*='LinkedIn Apply']"),
        page.locator("button, a"),
    ]
    for locator in locators:
        count = locator.count()
        for index in range(count):
            candidate = locator.nth(index)
            try:
                if not candidate.is_visible() or not candidate.is_enabled():
                    continue
                label = _clickable_label(candidate).lower()
                if "easy apply" in label or "linkedin apply" in label:
                    return candidate
            except Exception:
                continue
    return None


def _click_candidate(candidate) -> bool:
    try:
        candidate.scroll_into_view_if_needed(timeout=3000)
        candidate.click(timeout=5000)
        return True
    except Exception:
        try:
            candidate.evaluate("(el) => el.click()")
            return True
        except Exception:
            return False


def _clickable_label(candidate) -> str:
    try:
        return candidate.evaluate(
            """
            (el) => [
              el.innerText || el.textContent || '',
              el.getAttribute('aria-label') || '',
              el.getAttribute('title') || ''
            ].join(' ').replace(/\\s+/g, ' ').trim()
            """
        )
    except Exception:
        return ""


def _visible_clickable_labels(page) -> list[str]:
    labels: list[str] = []
    locator = page.locator("button, a")
    for index in range(min(locator.count(), 80)):
        candidate = locator.nth(index)
        try:
            if not candidate.is_visible():
                continue
            label = _compact_label(_clickable_label(candidate))
            if label:
                labels.append(label)
        except Exception:
            continue
    return labels


def _find_step_button(scope, actions: set[str]):
    locator = scope.locator("button, a")
    for index in range(locator.count()):
        candidate = locator.nth(index)
        try:
            if not candidate.is_visible() or not candidate.is_enabled():
                continue
            label = _clickable_label(candidate).lower()
            if _is_backward_or_exit_label(label):
                continue
            if _is_step_label(label, actions):
                return candidate
        except Exception:
            continue
    return None


def _is_step_label(label: str, actions: set[str]) -> bool:
    normalized = " ".join((label or "").lower().split())
    if not normalized:
        return False
    if _is_backward_or_exit_label(normalized):
        return False
    if "submit application" in actions and "submit application" in normalized:
        return True
    if "review" in actions and re.search(r"\breview\b", normalized):
        return True
    if "next" in actions and re.search(r"\bnext\b", normalized):
        return True
    if "continue" in actions and re.search(r"\bcontinue\b", normalized):
        return True
    return False


def _is_backward_or_exit_label(label: str) -> bool:
    normalized = " ".join((label or "").lower().split())
    return bool(re.search(r"\b(back|previous|cancel|dismiss|close|discard)\b", normalized))


def _application_modal(page):
    for selector in ["div[role='dialog']", ".jobs-easy-apply-modal", ".artdeco-modal"]:
        modal = page.locator(selector)
        if modal.count():
            return modal.first
    return page.locator("body")


def _detect_step(modal) -> str:
    text = _modal_text(modal).lower()
    if "submit application" in text or re.search(r"\breview\b", text):
        if _find_step_button(modal, {"submit application"}):
            return "review"
    if "resume" in text or "cv" in text:
        return "resume"
    if any(term in text for term in ["additional question", "work authorization", "sponsorship", "screening question"]):
        return "questions"
    return "personal_info"


def _modal_text(modal) -> str:
    try:
        return modal.evaluate("(el) => (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim()")
    except Exception:
        return ""


def _upload_resume_if_possible(modal, resume_path: Path, result: ApplyResult) -> bool:
    file_inputs = modal.locator("input[type='file']")
    for index in range(file_inputs.count()):
        field = file_inputs.nth(index)
        try:
            if not field.is_enabled():
                continue
            field.set_input_files(str(resume_path))
            marker = f"resume: {resume_path.name}"
            if marker not in result.filled_fields:
                result.filled_fields.append(marker)
            return True
        except Exception:
            continue
    if _detect_step(modal) == "resume":
        marker = "resume step: no enabled upload input found; existing resume may already be selected"
        if marker not in result.filled_fields:
            result.filled_fields.append(marker)
    return False


def _fill_visible_fields(modal, applicant: ApplicantProfile, result: ApplyResult) -> None:
    fields = modal.locator("input, textarea, select")
    for index in range(fields.count()):
        field = fields.nth(index)
        try:
            if not field.is_visible() or not field.is_enabled():
                continue
            field_type = (field.get_attribute("type") or "").lower()
            if field_type in {"hidden", "file", "button", "submit", "checkbox", "radio"}:
                continue
            label = _field_label(field)
            value = answer_for_label(label, applicant)
            if not value:
                continue
            tag = field.evaluate("(el) => el.tagName.toLowerCase()")
            if tag == "select":
                if _select_option_by_text(field, value):
                    result.filled_fields.append(_field_marker(label, value))
            else:
                current = field.input_value(timeout=1000) if tag == "input" else ""
                if not current.strip():
                    field.fill(value)
                    result.filled_fields.append(_field_marker(label, value))
        except Exception:
            continue


def _unknown_required_fields(modal, applicant: ApplicantProfile) -> list[str]:
    unknowns: list[str] = []
    fields = modal.locator("input, textarea, select")
    for index in range(fields.count()):
        field = fields.nth(index)
        try:
            if not field.is_visible() or not field.is_enabled():
                continue
            field_type = (field.get_attribute("type") or "").lower()
            if field_type in {"hidden", "file", "button", "submit"}:
                continue
            label = _field_label(field)
            if not _is_required(field):
                continue
            if answer_for_label(label, applicant):
                continue
            tag = field.evaluate("(el) => el.tagName.toLowerCase()")
            has_value = bool((field.input_value(timeout=1000) if tag in {"input", "textarea"} else "").strip())
            if not has_value:
                unknowns.append(_compact_label(label))
        except Exception:
            continue
    return unknowns


def _field_label(field) -> str:
    return field.evaluate(FIELD_LABEL_JS)


def _is_required(field) -> bool:
    return bool(field.evaluate(REQUIRED_JS))


def _select_option_by_text(field, value: str) -> bool:
    options = field.locator("option")
    desired = value.strip().lower()
    for index in range(options.count()):
        option = options.nth(index)
        text = (option.inner_text() or "").strip()
        if not text:
            continue
        normalized = text.lower()
        if normalized == desired or normalized.startswith(desired):
            field.select_option(label=text)
            return True
    return False


def _field_marker(label: str, value: str) -> str:
    return f"{_compact_label(label)}: {value}"


def _compact_label(label: str) -> str:
    text = " ".join(str(label or "").split())
    if len(text) <= 90:
        return text
    return text[:89].rstrip() + "…"
