# Twitch headed-browser verification

## Status

- Partial success. Fresh isolated headed Chrome opened target hosted form; application form remains visible in running Chrome.
- Five whitelisted profile controls filled and read back successfully.
- One selected PDF attached; attachment chip visible on form.
- 23 rendered required controls remain blank. Form did not reach final review.

## Blockers and safety

- Required unsupported/manual fields remain for human input, including legal/employment, citizenship, relocation, and other user-specific questions.
- Contact-country control left untouched; prior read-back instability remains unresolved.
- CAPTCHA not solved or interacted with. No submit control clicked; no application POST called.
- No profile values recorded in this artifact.

## Browser and screenshot

- Headed Chrome process remains running with fresh profile at `data/greenhouse-review-profile`; hosted application page visible.
- Screenshot: `data/greenhouse-review/twitch-8817023002-verification.png` (ignored local data only).
