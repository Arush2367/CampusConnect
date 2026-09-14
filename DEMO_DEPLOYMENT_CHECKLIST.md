# CampusConnect V20 — Demo Deployment Checklist

## Local demo
Run `setup_demo_env.ps1` once on Windows and enter the Gmail sender + Google App Password when prompted. This creates `.env.local`, which is ignored by Git.

Then start the app normally with `python server.py` (or the provided run script).

## Render
Set these environment variables in the Render service (do not commit them):
- `CAMPUSCONNECT_EMAIL_MODE=smtp`
- `CAMPUSCONNECT_SMTP_HOST=smtp.gmail.com`
- `CAMPUSCONNECT_SMTP_PORT=587`
- `CAMPUSCONNECT_SMTP_USERNAME=<sending Gmail>`
- `CAMPUSCONNECT_SMTP_APP_PASSWORD=<Google App Password>`
- `CAMPUSCONNECT_SMTP_FROM_NAME=Campus Connect`
- `CAMPUSCONNECT_PUBLIC_URL=<your Render URL>`
- `CAMPUSCONNECT_PRIMARY_ADMIN=<admin login id>`
- `CAMPUSCONNECT_BOOTSTRAP_ADMIN_NAME=<admin name>`
- `CAMPUSCONNECT_BOOTSTRAP_ADMIN_EMAIL=<admin email>`
- `CAMPUSCONNECT_BOOTSTRAP_ADMIN_PASSWORD=<strong admin password>`
- `CAMPUSCONNECT_BOOTSTRAP_ADMIN_MOBILE=<10 digit mobile>`

The source tree contains `.env.example` only; no real credentials are packaged.

## OTP/account creation verification
The supported flow is:
1. Student submits signup.
2. OTP email is sent.
3. Student enters the OTP.
4. Backend creates the student account in the active database.
5. Login ID is returned.
6. Login screen shows an explicit account-created success message and prefills the new login ID.
7. Student enters the password and signs in.

The account-creation code is database-backend neutral: PostgreSQL no longer relies on SQLite-only `last_insert_rowid()` behavior.


DEMO-ONLY NOTE
This V20 demo package intentionally contains the Gmail SMTP App Password because the user requested a self-contained demo package for tomorrow. Do not publish this repository publicly. Move the values to Render secret variables and rotate the App Password before any real deployment.
