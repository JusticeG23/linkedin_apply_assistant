# LinkedIn Apply Assistant

Small, truthful job-discovery assistant.

Current scope:

- Open a LinkedIn search preset or URL in Playwright.
- Extract visible job cards, then open detail pages before filtering.
- Filter against your criteria.
- Tag results with the search preset that found them.
- Store results in SQLite.
- Export TSV for review.

Not current scope:

- Auto-submitting applications.
- Guessing answers.
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

Pretty export is the default. Use TSV when you want spreadsheet-friendly output:

```bash
jobbot export --status needs_review --format tsv
```

Exports include this metadata:

```text
search_preset
```

Use the preset later to pick the right tailored resume packet for each candidate.

## Search Presets

Edit:

```text
config/searches.yaml
```

Each preset defines LinkedIn search filters:

```yaml
backend_platform:
  keywords: "software engineer backend platform data infrastructure"
  location: "Mountain View, California, United States"
  easy_apply: true
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
