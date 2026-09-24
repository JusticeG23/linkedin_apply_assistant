# Project Tasks

Last updated: 2026-09-23

Tracks Greenhouse POC in `PLAN.md`; use
`artifacts/greenhouse-contract-proposal.md` as approved starting contract. Do not
infer requirements beyond it.

## Completed

- Approved Greenhouse starting contract; paused LinkedIn development until POC
  passes.
- Added read-only one-URL inspection client and mocked tests (27 focused; 114
  full-suite passes). No live API or POST used.

## Active work

- [ ] Implement local application-plan generation using agreed field
      normalization and schema.
- [ ] Implement approved answer policy and Playwright fill/upload/read-back;
      block unsupported required fields and required cover letters, never submit.
- [ ] Add endpoint/DOM fixtures and verify one end-to-end Greenhouse POC path
      stops at the agreed pre-submit state.

## Superseded by Greenhouse POC

Do not build further LinkedIn-specific behavior: job search/discovery, job-fit
screening and LLM judge, SQLite queue/export, or LinkedIn Easy Apply. Existing
files remain until Greenhouse POC passes; preserve a rollback copy before later
removal.

## Validation baseline

`.venv/bin/pytest -q` — 114 passed. This includes mocked Greenhouse URL/API
tests; no live API, browser, or application-submit flow has been exercised.
`.venv/bin/jobbot --help` still works for legacy CLI.
