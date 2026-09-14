# Campus Connect — Final Clean Build

This build uses the Phase 3 backend, API contracts and database workflow as the functional source of truth, with a redesigned student/admin UI layered on top.

## Run

Windows: `run.bat` or `py server.py`

Default URL: `http://localhost:3000`

## Functional rule

Do not replace backend route contracts when changing the UI. The V3 backend is the stable integration surface.

## Student email OTP verification
Students must verify their email before account creation. Copy `.env.example` to `.env`, enable 2-Step Verification on the sending Google account, create a Google App Password, and set the SMTP username and App Password. Never put the normal Google account password in the project.
