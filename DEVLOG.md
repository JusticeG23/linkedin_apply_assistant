# LinkedIn Apply Assistant Dev Log

Last reviewed: 2026-09-23

## Transition status

Project direction has pivoted from LinkedIn job discovery/Easy Apply to Ethan's
Greenhouse-only, one-URL application-preparation POC. Current source tree is the
legacy LinkedIn baseline plus Greenhouse inspection, plan generation, and partial
fill/read-back helpers. End-to-end browser application flow remains incomplete.

## Legacy implementation

`jobbot` is a local Python CLI with LinkedIn login, search/discovery, canonical
job-page extraction, deterministic screening, optional advisory job judge,
SQLite queue/export, and LinkedIn Easy Apply assistance. Most tests validate
legacy behavior; Greenhouse tests cover read-only URL/API inspection only. The
uncommitted LinkedIn work is frozen until POC passes, then scheduled for cleanup.

## Greenhouse POC status

Approved contract defaults are recorded in
`artifacts/greenhouse-contract-proposal.md`. Read-only URL/API inspection exists;
local plan generation and browser fill/verification remain unimplemented. Source
files stay in place until the POC passes and rollback copy is saved.

Twitch job `8817023002` was inspected with public GET. Plan includes 25
application, 3 compliance, and 3 location questions; 24 required-input blockers
remained without applicant/resume inputs. A local headed-browser attempt then
filled/read back five profile controls and verified PDF; 18 required questions,
one phone-country read-back issue, and CAPTCHA still block final review. Initial
plan omitted location questions; synthetic tests caught/fixed this. Coverage
includes location, demographic-object, required-cover-letter, and consent
branches. `.venv/bin/pytest -q` — 125 passed. No LLM, application POST, or final
submission ran. See `PLAN.md`, `TASKS.md`, and `DECISIONS.md` for canonical state.
