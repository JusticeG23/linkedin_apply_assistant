# Twitch application-plan run

## Result

- Input: `https://job-boards.greenhouse.io/twitch/jobs/8817023002`.
- Canonical generated plan: `data/greenhouse-plans/twitch-8817023002.json`.
- Public Greenhouse Job Board `GET` only. No applicant/resume files, browser,
  LLM, application `POST`, or submit used.
- Plan contains 25 application, 3 compliance, 3 required location questions, 0
  demographic questions, office/location metadata, and GDPR policy flags.
- No applicant profile, resume paths, proposed answers, personal excerpts, or
  approvals supplied. Plan reports 24 blockers: 5 missing local facts (name,
  email, phone, location) and 19 required manual inputs, including resume and
  user-specific questions. Twitch consent flags are explicitly false.

## Review findings and coverage

- Initial output omitted 3 required `location_questions` and underreported
  blockers (21). Planner review caught omission; normalizer now includes location
  fields and produces 24 blockers.
- Synthetic tests cover required cover-letter blocking, official demographic
  `{ "questions": [...] }` shape, required location fields, and required consent
  flags. Consent is never inferred or approved.
- Generated plan records API sources, answer class, source/evidence placeholders,
  proposed value, per-value approval, and verification state.

## Validation

- Focused plan tests: 5 passed.
- Full suite: 121 passed.
- `git diff --check` passed.
- No browser flow or end-to-end application preparation validated.
