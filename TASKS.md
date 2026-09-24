# Project Tasks

Last updated: 2026-09-23

Tracks Greenhouse POC in `PLAN.md`; use
`artifacts/greenhouse-contract-proposal.md` as approved starting contract. Do not
infer requirements beyond it.

## Completed

- Approved Greenhouse starting contract; paused LinkedIn development until POC
  passes.
- Added read-only inspection and local plan generation; full suite passes.
- Exercised Twitch plan through public GET. Output: 25 application, 3 compliance,
  and 3 location questions; 24 blockers remain because no local profile, resume,
  or approved answers were supplied. No browser, LLM, application POST, or submit.
- Synthetic coverage tests required cover letter, location, demographic-object,
  and consent branches.
- Attempted local headed-browser fill with profile and data-platform resume. Five
  profile controls read back; PDF verified. Eighteen required questions remain,
  phone-country read-back unstable, and CAPTCHA remains unsolved. No submit.

## Active work

- [ ] Make Twitch fill repeatable from approved local inputs and resolve supported
      contact-country read-back. Keep unsupported questions, CAPTCHA, and unknown
      legal/employment answers for human input; never submit.
- [ ] Add endpoint/DOM fixtures and verify one end-to-end Greenhouse POC path
      stops at the agreed pre-submit state.
- [ ] After review and validation, commit and push relevant files without force;
      exclude IDE/scratch files and private/generated data.
- [ ] After review and validation, commit and push only relevant Greenhouse POC,
      project-state, and approved agent-policy files. Exclude IDE/scratch files,
      stale legacy notes, and private/generated data.

## Superseded by Greenhouse POC

Do not build further LinkedIn-specific behavior: job search/discovery, job-fit
screening and LLM judge, SQLite queue/export, or LinkedIn Easy Apply. Existing
files remain until Greenhouse POC passes; preserve a rollback copy before later
removal.

## Validation baseline

`.venv/bin/pytest -q` — 125 passed. Twitch public GET and local browser fill
attempt ran; no LLM, application POST, or submission flow was used. Form has not
reached final review.
`.venv/bin/jobbot --help` still works for legacy CLI.
