# Project Plan

Last updated: 2026-09-23

## Product goal

Given one Greenhouse job URL, inspect its application, prepare and verify a
reviewable application, then stop for the user. The user always reviews and
submits.

## POC scope

- Extract application fields, types, options, and required status.
- Fill known facts from a private local profile.
- Generate only approved short-text answers, grounded in explicit evidence.
- Upload the explicitly selected PDF resume; use Markdown resume only as LLM
  evidence.
- Verify filled values, report blockers, and leave browser open before submit.
- Support Greenhouse only. Never click submit, create/upload cover letters, guess
  unsupported facts, or solve CAPTCHAs. A required cover letter or unsupported
  required field blocks the run.

## Current state and transition

The repository contains a LinkedIn CLI and substantial legacy implementation,
plus isolated Greenhouse inspection and plan-generation code. Do not extend
LinkedIn features; retain that code until POC passes, then save a rollback copy
before cleanup. Twitch plan generation identified missing applicant/resume inputs.
A local headed-browser attempt then filled and read back 5 profile controls and
verified selected PDF. Eighteen required API blockers, one unstable phone-country
control, and CAPTCHA remain; form did not reach final review. Full suite: 125
tests pass.

Ethan's draft had blank implementation contracts. Their starting defaults are
now approved in `artifacts/greenhouse-contract-proposal.md`: inspection endpoint,
pre-submit stop point, private input paths/schema, answer classes, approval gate,
and plan format. Implement to that contract; revise it before coding if new
evidence requires a change.

## Milestone: one-URL Greenhouse POC

1. Approve starting contract defaults in
   `artifacts/greenhouse-contract-proposal.md` — complete.
2. Retain the current LinkedIn baseline until Greenhouse POC passes; do not
   develop it further or delete it during the POC transition.
3. Inspect one Greenhouse application and produce a local plan containing field
   type/options/required status, proposed values, sources, evidence, confidence,
   and verification status — complete for Twitch; plan reports missing inputs.
4. Apply only policy-approved plan values; upload the selected PDF; read back and
   verify values; report blockers; stop at the agreed pre-submit state.
5. Add mocked endpoint/DOM fixtures for extraction, answer policy, upload,
   verification, and every blocking condition. Validate one end-to-end POC path
   without submitting.

## Success criteria

For one supplied Greenhouse URL, produce a verified, reviewable application or
an actionable blocker report. Every proposed answer has an allowed source;
private profile never reaches the LLM; unsupported required fields stop the
flow; the chosen PDF is verified; browser remains at the specified review point;
final submission is never automated.

## Superseded

LinkedIn discovery, job-fit screening, SQLite queue/export, and LinkedIn Easy
Apply are outside the new POC. See `TASKS.md` for transition tasks and
`DECISIONS.md` for retained safety constraints.
