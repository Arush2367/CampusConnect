
# Deploy Campus Connect to Vercel

This project exposes the Python API as Vercel Functions under `api/` and keeps
the frontend and API on the same HTTPS domain. Do not run `server.py` as a web
server on Vercel; Vercel invokes the `handler` classes automatically.

## Before deployment

1. Create a managed PostgreSQL database (Vercel Postgres, Neon, Supabase, or
   another PostgreSQL provider) and obtain its SSL-enabled connection string.
2. In **Vercel → Project → Settings → Environment Variables**, add these for
   **Production**. Enter real values there; never put them in Git.

   - `CAMPUSCONNECT_ENV=production`
   - `CAMPUSCONNECT_HTTPS=1`
   - `CAMPUSCONNECT_PUBLIC_URL=https://YOUR-PROJECT.vercel.app`
   - `DATABASE_URL` — PostgreSQL connection string
   - `CAMPUSCONNECT_EMAIL_MODE=smtp`
   - `CAMPUSCONNECT_SMTP_HOST=smtp.gmail.com`
   - `CAMPUSCONNECT_SMTP_PORT=587`
   - `CAMPUSCONNECT_SMTP_USERNAME` — Gmail sender address
   - `CAMPUSCONNECT_SMTP_APP_PASSWORD` — Gmail App Password
   - `CAMPUSCONNECT_SMTP_FROM_NAME=Campus Connect`
   - `CAMPUSCONNECT_PRIMARY_ADMIN=ADMIN001`
   - `CAMPUSCONNECT_BOOTSTRAP_ADMIN_NAME`
   - `CAMPUSCONNECT_BOOTSTRAP_ADMIN_EMAIL`
   - `CAMPUSCONNECT_BOOTSTRAP_ADMIN_PASSWORD` — long random password
   - `CAMPUSCONNECT_BOOTSTRAP_ADMIN_MOBILE`

3. Set the Vercel project's **Root Directory** to the folder containing
   `vercel.json`. Leave the framework preset as **Other** and do not add a
   build or start command.
4. Deploy. Visit `/api/health`; it must return `{"status":"ok"}` before
   testing signup or login.

## Security

The packaged `.env` is only a safe local template and is excluded from Vercel
deployments. If this project was previously public with real `.env` values,
rotate the SMTP App Password and bootstrap-admin password before redeploying.
