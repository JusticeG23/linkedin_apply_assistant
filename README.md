# LinkedIn Apply Assistant

> **Project pivot in progress:** target is a Greenhouse-only, one-URL
> application-preparation POC. Existing instructions below describe the legacy
> LinkedIn CLI and are not the new POC interface. Greenhouse support currently
> consists only of a read-only inspection library; no application UI/CLI flow is
> wired yet.

Legacy LinkedIn job-discovery assistant.

Legacy LinkedIn CLI capabilities:

- Preview one LinkedIn job URL as a job-fit lint report.
- Open the canonical detail page before filtering.
- Extract top metadata and cleaned job-description sections.
- Filter against your criteria.
- Print evidence, required/preferred section summaries, and a copyable TSV row.
- Optionally run an advisory LLM section judge after cheap deterministic filters.

Still available, but not the current MVP focus:

- Search/discovery.
- SQLite commit/export flow.

Not current scope:

- Guessing answers.
- Auto-submitting applications without manual review.
- Misrepresenting skills.

## Setup

```bash
cd /Users/jbgarner/Documents/Codex/2026-06-17/this-is-a-previous-chat-i/linkedin_apply_assistant
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
playwright install chromium
```

## First Run

Use a dedicated browser profile. Log in to LinkedIn once when the browser opens.

```bash
jobbot login
```

The browser stays open until you press Enter in the terminal. After login, the session is saved under:

```text
data/browser-profile
```

## Discovery

Recommended preset flow:

```bash
jobbot discover --preset backend_platform --headful --keep-open
```

By default, discovery hydrates and reviews 5 postings. Each posting is shown
with its classification, including rejected jobs. You choose whether to commit
each one to SQLite:

```text
Commit to DB? [y/N/q]
```

Use `--limit` when you want a larger review batch:

```bash
jobbot discover --preset backend_platform --limit 10
```

Other presets:

```bash
jobbot discover --preset data_platform --headful --keep-open
jobbot discover --preset ai_infra --headful --keep-open
jobbot discover --preset reliability --headful --keep-open
```

Discovery opens each reviewed job's detail page before filtering. Card-only
results are skipped because they are too low-confidence for requirements/YOE
filtering. Nothing is written to SQLite until you explicitly approve it.

Manual URL flow:

```bash
jobbot discover \
  --search-url "https://www.linkedin.com/jobs/search/?keywords=software%20engineer%20backend%20platform%20data%20infrastructure&location=Mountain%20View%2C%20California%2C%20United%20States&distance=10&f_AL=true&f_TPR=r604800&f_WT=1%2C3&sortBy=DD" \
  --headful
```

If you want the browser to stay open after discovery:

```bash
jobbot discover \
  --search-url "https://www.linkedin.com/jobs/search/?keywords=software%20engineer%20backend%20platform%20data%20infrastructure&location=Mountain%20View%2C%20California%2C%20United%20States&distance=10&f_AL=true&f_TPR=r604800&f_WT=1%2C3&sortBy=DD" \
  --headful \
  --keep-open
```

Then export:

```bash
jobbot export --status needs_review
```

Preview one job without writing to SQLite:

```bash
jobbot preview --job-url "https://www.linkedin.com/jobs/view/4451659487/" --headful
```

Print extracted sections before classification:

```bash
jobbot preview --job-url "https://www.linkedin.com/jobs/view/4451659487/" --headful --debug-sections
```

Preview one job with the advisory LLM section judge:

```bash
OPENAI_API_KEY=... jobbot preview --job-url "https://www.linkedin.com/jobs/view/4451659487/" --headful --llm-rules
```

The LLM check uses the canonical detail page and sends only top job metadata
plus required/minimum qualification sections. Preferred, overview, and
responsibility sections are intentionally omitted to reduce token spend. The
LLM result prints below the deterministic classifier result. It does not write
to SQLite.
If cheap deterministic filters reject a job for things like location, role
mismatch, Easy Apply, or base pay, the LLM call is skipped to save spend. Use
`--force-llm` when you explicitly want to inspect the LLM read anyway.

Pretty export is the default. Use TSV when you want spreadsheet-friendly output:

```bash
jobbot export --status needs_review --format tsv
```

Exports include this metadata:

```text
search_preset
```

Use the preset later to pick the right tailored resume packet for each candidate.

## LinkedIn Easy Apply Fill

After a role passes preview and you want to apply, use:

```bash
jobbot apply \
  --job-url "https://www.linkedin.com/jobs/view/4296093604/" \
  --resume-family backend_engineer
```

The command:

- opens the canonical LinkedIn job detail page
- clicks Easy Apply when available
- attaches the matching PDF from `/Users/jbgarner/Documents/resume/role_families/<resume_family>/`
- fills only known safe fields from `config/applicant.yaml`
- stops on unknown required fields, free-text questions, or blockers
- pauses before final submit so you can inspect everything yourself

It never clicks `Submit application`.

Applicant config:

```bash
cp config/applicant.example.yaml config/applicant.yaml
```

Then edit `config/applicant.yaml` locally. It contains personal contact data, so
it is intentionally ignored by git.

Available resume families are the subdirectories under:

```text
/Users/jbgarner/Documents/resume/role_families
```

Common examples:

```bash
jobbot apply --job-url "https://www.linkedin.com/jobs/view/..." --resume-family backend_engineer
jobbot apply --job-url "https://www.linkedin.com/jobs/view/..." --resume-family data_engineer
jobbot apply --job-url "https://www.linkedin.com/jobs/view/..." --resume-family distributed_systems
jobbot apply --job-url "https://www.linkedin.com/jobs/view/..." --resume-family full_stack_engineer
```

Use `--close-when-done` only when you do not need the browser left open for
inspection.

## Search Presets

Edit:

```text
config/searches.yaml
```

Each preset defines LinkedIn search filters:

```yaml
defaults:
  location: "Mountain View, California, United States"
  distance: 10
  easy_apply: true
  posted_within: r604800
  sort_by: DD
  work_type:
    - onsite
    - hybrid
  experience:
    - mid_senior

backend_platform:
  keywords: "software engineer backend platform data infrastructure"
```

## Criteria

Edit:

```text
config/criteria.yaml
```

The filter is intentionally conservative. It rejects:

- hard `>5 years` requirements
- obvious data-science/ML-research requirements
- frontend-heavy roles
- remote-only roles
- locations outside the Mountain View / Palo Alto / Sunnyvale / Santa Clara / San Mateo / Redwood City band
- likely base pay below target

Farther locations can be allowed only when the role is hybrid by adding them to
`hybrid_allowed_locations` in `config/criteria.yaml`.

Contextual hard-gap rules live in:

```text
config/context_rules.yaml
```

These use RapidFuzz over short context windows, so phrases like `PhD preferred`
or `Kubernetes preferred` do not reject the job, while `PhD required` or
`Must have production Kubernetes experience` can still reject it.

## Data

SQLite DB:

```text
data/jobs.sqlite
```
