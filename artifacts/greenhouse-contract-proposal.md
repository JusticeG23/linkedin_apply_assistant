# Greenhouse POC contract proposal

Status: user approved as the Greenhouse POC starting contract. Implementation
must still follow existing human-review and no-submit constraints.

## One-URL inspection

- Accept one public Greenhouse hosted-board URL shaped as
  `https://boards.greenhouse.io/{board_token}/jobs/{job_id}`. Reject unrecognized
  hosts/paths rather than guessing board identity.
- Read form definition from the public, unauthenticated endpoint:
  `GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}?questions=true`.
- Reconcile API fields with rendered hosted-form DOM before filling. DOM is
  needed to verify actual controls and values; API response is source for
  question IDs, required flags, options, compliance/location/demographic fields.
- Do not call Greenhouse's application `POST` endpoint. It requires an API key
  and submits the application; POC must leave final submission to the user.

Official references:

- [Greenhouse Job Board API — Retrieve a job](https://developers.greenhouse.io/job-board.html#retrieve-a-job)
- [Greenhouse Job Board API — Submit an application](https://developers.greenhouse.io/job-board.html#submit-an-application)

## Proposed local inputs

- Private facts: `config/applicant.yaml`, Git-ignored. Start with explicit
  fields for name, email, phone, location, work authorization, and sponsorship.
  Add fields only when user provides schema. Never send this file or values read
  from it to an LLM.
- Resume: require `--resume-md` and `--resume-pdf` paths on each run. Read
  Markdown locally for evidence; upload PDF only. Do not choose a resume family
  implicitly.
- Reviewed short-answer source: propose `config/short_answers.yaml`, also
  Git-ignored, with user-authored answer snippets and topic tags. Do not create
  or populate it without user-provided content.

Proposed initial profile keys: `first_name`, `last_name`, `email`, `phone`,
`location`, `work_authorized_us`, and `needs_sponsorship`; the last two are
optional booleans. Demographic facts are not part of POC profile schema.

Proposed short-answer structure:

```yaml
answers:
  - id: project-example
    topic: project
    excerpt: "User-authored, reviewed answer evidence"
    reviewed: true
```

Only entries with `reviewed: true` and an eligible `topic` may be provided to
the LLM. No file is generated with fabricated/example user content.

## Proposed answer classes

1. `known_fact`: exact local-profile mapping; no LLM.
2. `eligible_draft`: LLM may draft only motivation, experience, project,
   accomplishment, or role-fit short text, using the question plus only relevant
   excerpts from Markdown resume and reviewed short-answer snippets.
3. `manual`: compliance, demographic, consent, ambiguous, or otherwise
   user-specific fields. Never infer consent or sensitive answers. Leave
   optional fields untouched; for required fields, stop automation and leave the
   browser open with a blocker for the user.
4. `unsupported`: unknown type/source or required cover letter. Do not fill; if
   required, stop and report blocker.

Every proposal records exact source paths/excerpts. LLM confidence is
informational, not approval. Recommended gate: show complete plan and require
explicit human approval before browser fill; unsupported required fields remain
blocked.

## Proposed application plan

- File: `data/greenhouse-plans/{board_token}-{job_id}.json` (`data/` is
  Git-ignored).
- Record job URL/identity, explicit resume paths, API/DOM fields, type/options/
  required state, proposed value, answer class, source/evidence, model/confidence
  when relevant, human approval, and post-fill verification status.
- Each field has `approval: pending|approved|rejected` and
  `verification: not_attempted|verified|mismatch`.
- Produce `proposed` plan first. Human reviews each proposed value; only
  individually approved values enter the browser. LLM confidence is
  informational and never grants approval.

## Proposed stop point

After approved values and PDF are filled and read back successfully, leave browser
open at Greenhouse's final review page immediately before the submit control.
Never click submit. If no distinct review page exists, leave browser open with
completed form immediately before submission and report that state.

## Accepted defaults

- Restrict initial URL input to the stated hosted-board path; do not infer
  support for custom career-site domains or alternate URL shapes.
- Required manual/sensitive fields stop automation and are reported; optional
  manual/sensitive fields remain untouched.
- Human approval is per proposed value. Optional demographic fields remain
  untouched; no demographic automation in this POC.
