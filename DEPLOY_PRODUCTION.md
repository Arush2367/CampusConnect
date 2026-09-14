# CampusConnect production deployment

## GitHub safety
- Commit `.env.example`, never `.env`.
- The production database and uploaded files are ignored by Git.
- Put SMTP credentials and bootstrap-admin secrets in the host's environment/secrets settings.

## Render
1. Push this repository to GitHub.
2. Create a Render Web Service from the repository, or use `render.yaml`.
3. Add the environment values marked `sync: false` in Render's Environment settings.
4. Set `CAMPUSCONNECT_PUBLIC_URL` to the final HTTPS URL.
5. Deploy and test: `/`, signup, OTP, login, student dashboard, admin dashboard.

## Production accounts
Demo credentials are disabled when `CAMPUSCONNECT_SEED_DEMO=0`.
If the database has no administrator, the server bootstraps `CAMPUSCONNECT_PRIMARY_ADMIN` using the configured bootstrap environment variables.

## Gmail OTP
Use a Google App Password, not the normal Google account password. Never place the secret in source code, `.env.example`, screenshots, or GitHub.
