# Twitch pre-submit fill attempt

## Counts

- Form questions: 25 application, 3 compliance, 3 location, 0 demographic.
- Filled/read-back verified: 5 profile controls; selected PDF attachment: 1, verified.
- Authored short-answer snippets used: 0.
- Remaining blockers: 18 required API fields plus 1 rendered required contact-country control; CAPTCHA widget present.

## Filled controls

- `application:first_name` — First Name
- `application:last_name` — Last Name
- `application:email` — Email
- `application:phone` — Phone
- `location:location` — Location (City)
- `application:resume|resume_text` — Resume/CV (PDF attachment)

Rendered `application:country` — Country (Phone) did not retain stable read-back; left for human review.

## Required blockers left blank

- `location:longitude` — Longitude
- `location:latitude` — Latitude
- `application:question_38381132002` — How would you describe your experience with Twitch? (Select one)
- `application:question_38381133002` — How many years have you been active on the platform?
- `application:question_38381134002[]` — Do you have experience in the Creator Economy beyond Twitch?
- `application:question_38381135002` — Are you currently a Twitch employee?
- `application:question_38381136002` — Are you open to relocation?
- `application:question_38381137002` — Are you a current employee with Amazon or any Amazon subsidiary (outside of Twitch)?
- `application:question_38381138002` — Have you previously applied to Amazon or any Amazon subsidiary?
- `application:question_38381139002` — Have you previously been employed by Amazon or any Amazon subsidiary?
- `application:question_38381140002` — Are you subject to a non-competition agreement or other agreement that would preclude or restrict your employment at Amazon?
- `application:question_38381141002` — If offered employment by Amazon, would you be legally eligible to begin employment immediately?
- `application:question_38381142002` — Your response is mandatory when applying for a U.S.-based position. Do you need, or will you need in the future, any immigration related support or sponsorship from Amazon in order to begin or continue employment with Amazon?
- `application:question_38381143002` — Have you held H-1B status, or had an H-1B petition approved on your behalf, within the preceding 6 years for an employer other than a cap exempt institution?
- `application:question_38381144002[]` — In which country/region do you have citizenship?
- `application:question_38381145002` — Since obtaining your most recent citizenship, did you afterwards become a permanent resident in any other country/region?
- `application:question_38381146002` — For the sole purpose of determining export licensing requirements, please provide your country of citizenship or legal permanent residence, whichever was obtained last.
- `application:question_38381148002` — Would you like to be considered for future opportunities at Twitch when you apply?

## Browser and safety

- Headed Chrome window remains open and visible in dedicated local profile at hosted form. Browser bridge is disconnected; no live Review-pane link available.
- CAPTCHA not solved. Submit control not clicked; application POST not called.

## Test evidence

- Added 4 synthetic tests: unsupported required control, explicit-profile whitelist, stale-value read-back, and mismatch reporting.
- `.venv/bin/pytest -q`: 125 passed.
- `git diff --check`: passed.
