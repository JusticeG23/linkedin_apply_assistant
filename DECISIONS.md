# Decisions and Product Constraints

Last updated: 2026-09-23

## D-001: Keep application submission human-controlled

**Decision:** Never click the final submit control. Stop at the agreed
pre-submission review point. Unsupported required fields and required cover
letters block the run. Eligible short-text generation is allowed only under the
completed answer policy and approved evidence sources.

**Reason:** The user owns final application content and submission. Unknown facts
must not be guessed.

## D-002: Greenhouse-only, one-URL POC

**Decision:** Target one supplied Greenhouse job URL. Do not build LinkedIn
discovery or support other applicant-tracking systems in this POC.

**Reason:** Greenhouse application preparation gives project a narrower,
measurable end-to-end target. Current LinkedIn functionality is legacy, not POC
scope.

## D-003: Keep applicant profile local and LLM inputs bounded

**Decision:** Private applicant profile stays local and is never sent to an LLM.
PDF resume is for upload only; Markdown resume is evidence for eligible
short-text answers. Only relevant, reviewed excerpts from the approved answer
source may be sent. Use accepted starting schemas/classifications in
`artifacts/greenhouse-contract-proposal.md`.

**Reason:** Personal data and answer provenance need explicit boundaries. Any
later changes to accepted defaults require a recorded decision.

## D-004: Preserve legacy work before destructive cleanup

**Decision:** Retain existing LinkedIn code until the Greenhouse POC passes; do
not develop it further. Before later deletion/replacement, save a rollback copy.

**Reason:** The working tree includes substantial uncommitted work. Reversible
transition avoids accidental loss while prioritizing Greenhouse POC.

## Legacy LinkedIn decisions

These apply only to the retired LinkedIn flow; they are not Greenhouse POC
requirements:

- Canonical LinkedIn job detail pages as screening evidence.
- Deterministic job-fit filters before an advisory job-requirements judge.
- Human approval before inserting discovered jobs into SQLite.
- SQLite as storage for LinkedIn discovery queue/export.

The Greenhouse POC does not yet require job screening, LLM job judging, a job
queue, or SQLite. See `PLAN.md` and `TASKS.md` for current scope and blockers.
