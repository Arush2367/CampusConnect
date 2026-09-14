# Campus Connect — Gmail OTP setup

Student signup now sends a 6-digit verification code through Gmail SMTP.

1. Use a dedicated Gmail/Google account for Campus Connect.
2. Enable Google 2-Step Verification on that account.
3. Create a Google App Password for Campus Connect.
4. Copy `.env.example` to `.env`.
5. Set:
   - `CAMPUSCONNECT_SMTP_USERNAME` = the sending Gmail address
   - `CAMPUSCONNECT_SMTP_APP_PASSWORD` = the generated 16-character App Password
6. Start the server normally.

Do not put the regular Google account password in `.env` or source code. The application only expects an App Password for SMTP authentication.

For tests without real email delivery, set `CAMPUSCONNECT_EMAIL_MODE=test`; the test transport writes the OTP to `data/test_email_outbox.jsonl`.


## Simple `.env` setup
Create a file named `.env` beside `server.py` and add either the `CAMPUSCONNECT_*` names above or these shorter aliases:

`SMTP_HOST=smtp.gmail.com`
`SMTP_PORT=587`
`SMTP_EMAIL=your-sending-gmail@gmail.com`
`SMTP_APP_PASSWORD=your-16-character-google-app-password`

The App Password may be pasted with or without the spaces Google displays. The password is never committed to the project.
