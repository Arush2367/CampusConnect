# CampusConnect V19 — PostgreSQL Production Mode

V19 keeps the existing SQLite path for local development and adds a PostgreSQL
backend for public deployments. Set `DATABASE_URL` to a PostgreSQL connection
string and the application automatically uses PostgreSQL; leave it unset to
retain the local SQLite behavior.

## Render deployment

Use a Render PostgreSQL database and connect its `connectionString` to the web
service as `DATABASE_URL`. Keep the existing persistent disk for user-uploaded
assets and other runtime files.

Required production environment values include:

- `CAMPUSCONNECT_ENV=production`
- `CAMPUSCONNECT_HOST=0.0.0.0`
- `DATABASE_URL=<Render PostgreSQL connection string>`
- `CAMPUSCONNECT_EMAIL_MODE=smtp`
- `CAMPUSCONNECT_SMTP_USERNAME=<Gmail sender>`
- `CAMPUSCONNECT_SMTP_APP_PASSWORD=<Google App Password>`
- `CAMPUSCONNECT_BOOTSTRAP_ADMIN_PASSWORD=<long random password>`
- `CAMPUSCONNECT_BOOTSTRAP_ADMIN_EMAIL=<admin email>`
- `CAMPUSCONNECT_PRIMARY_ADMIN=ADMIN001`

Secrets must be set in the hosting provider's environment/secret settings.
Do not commit `.env` or any secret values to GitHub.

## Data migration

A fresh production deployment creates the current schema in PostgreSQL and
bootstraps the administrator from environment variables. The local SQLite
file is intentionally left untouched. Existing SQLite data can remain for
local/demo use; migrate production data separately only when needed.

## Scaling boundary

PostgreSQL removes SQLite's single-file write bottleneck and is the correct
persistence layer for a multi-user public deployment. The application is still
designed as a single web service; horizontal scaling would additionally need
centralized/session-safe rate limiting and external object storage for uploads.
