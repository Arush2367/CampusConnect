# CampusConnect V19 — PostgreSQL Production Backend

- Added optional PostgreSQL backend selected by `DATABASE_URL`.
- Preserved SQLite behavior when `DATABASE_URL` is absent, so local/demo workflows remain unchanged.
- Added a compatibility layer for existing parameterized SQL, SQLite date helpers, `last_insert_rowid()`, and `INSERT OR IGNORE`.
- Converted the existing schema automatically for PostgreSQL on first production boot.
- Added PostgreSQL-aware column migrations and skipped legacy SQLite-only introspection in fresh PostgreSQL deployments.
- Updated Render Blueprint to provision and link a managed PostgreSQL database.
- Kept the persistent disk for user-uploaded/runtime files.
- Added PostgreSQL production deployment documentation.
- No frontend/UI changes.
