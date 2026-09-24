# LinkedIn Apply Assistant Dev Log

Last reviewed: 2026-09-23

## Transition status

Project direction has pivoted from LinkedIn job discovery/Easy Apply to Ethan's
Greenhouse-only, one-URL application-preparation POC. Current source tree is the
legacy LinkedIn baseline plus an isolated read-only Greenhouse inspector. No
end-to-end Greenhouse application flow exists yet. Do not treat inspection tests
as browser/application validation.

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

`.venv/bin/pytest -q` — 114 passed, including mocked Greenhouse URL/API
inspection tests. No live API, browser, form-fill, or submission workflow was
run. See `PLAN.md`, `TASKS.md`, and `DECISIONS.md` for canonical target, sequence,
and safety constraints.
