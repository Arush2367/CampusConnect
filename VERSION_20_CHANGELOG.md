# Version 20 — Production Demo OTP + Account Creation Fix

- Fixed student OTP verification account creation to be database-backend neutral.
- Fixed PostgreSQL student-account ID retrieval by querying the newly created unique username instead of relying on SQLite-only last_insert_rowid semantics.
- Fixed the signup success UX so the created login ID and success message remain visible on the login card after verification.
- Login ID is prefilled after successful verification; password remains blank and must be entered by the student.
- SMTP settings are re-read dynamically at send time, so local/demo or Render environment changes are picked up after restart without stale module-level values.
- Added .env.local support for local/demo configuration.
- Added a setup_demo_env.ps1 helper that writes local Gmail SMTP settings without placing credentials in source control.
- Kept real secrets out of the repository/ZIP.
