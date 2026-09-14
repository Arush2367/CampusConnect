# Version 17 — Student Email OTP Verification

- Student signup now requires a valid email and 6-digit OTP verification before creating the account.
- OTPs expire in 5 minutes, are single-use, hashed at rest, and limited to 5 attempts.
- Resend cooldown is 45 seconds.
- Added Gmail SMTP delivery via environment variables; no credentials are stored in source control.
- Staff/admin signup approval flow remains unchanged.
- Added a signup verification card that reuses the existing Campus Connect auth/card design language.
- Added test transport for automated integration tests without sending real email.


## V17.1 OTP configuration fix

- Added automatic loading of a project-root `.env` file at startup without a third-party dependency.
- Accepts both `CAMPUSCONNECT_SMTP_*` variables and the shorter `SMTP_*` aliases.
- Google App Passwords may be entered with or without the spaces shown by Google.
- Removed duplicate local `.env` loading logic from the mailer.
- Updated the integration test for the new signup -> OTP -> account creation flow.
