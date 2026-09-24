# Shared Agent Context

## Project

Build Greenhouse-only, one-URL application-preparation POC. User reviews and
submits. Current code has read-only inspection, plan generation, and partial
fill/read-back helpers in `src/greenhouse_apply_assistant/`. Full suite: 125
tests pass. Twitch form attempt remains blocked before final review.

## Hard constraints

- Never submit or call Greenhouse application `POST` endpoint.
- Keep applicant profile local; never send profile to LLM. Markdown resume is
  evidence only; explicitly selected PDF is upload only.
- Use approved per-value answers only. Unknown facts are never guessed.
- Unsupported required or required manual/sensitive fields block automation;
  stop before submit and leave browser for human review.
- Greenhouse-only. Stop LinkedIn development; retain legacy code until POC passes.
  Save rollback copy before later cleanup.

## Canonical project state

Planner owns `PLAN.md`, `TASKS.md`, and `DECISIONS.md`. Read these before work;
use `artifacts/greenhouse-contract-proposal.md` as approved starting contract.
Do not infer beyond that contract. Load other files/artifacts only when relevant.
Prefer scoped worker briefs with file references over repeating project context.
