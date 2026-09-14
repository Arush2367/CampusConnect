# CampusConnect security notes

- Secrets are loaded from process environment variables or local `.env` only; `.env` is gitignored.
- Production disables demo account seeding by default.
- Production sessions use secure, HTTP-only cookies.
- API/static responses include baseline security headers.
- Request bodies are size-limited.
- Passwords use scrypt hashing and OTPs are hashed before storage.
- User-provided images are restricted to safe raster image data URLs.
- SQL queries use parameterized statements throughout the application.
- Do not commit `data/campusbuddy.db`, runtime uploads, OTP outboxes, or provider credentials.
