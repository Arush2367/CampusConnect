# CampusLock v5 Architecture

## Trust boundaries
Browser → HTTP API → session/permission layer → SQLite transaction layer → audit/notification/event records.

## Core modules
- `server.py`: API routing, authentication, authorization, validation, transactions, state machines, audit, notification creation, QR generation.
- `public/index.html`: existing CampusLock shell and authentication shell.
- `public/app.js`: UI state, routing, fetch calls, view rendering, role-aware navigation.
- `public/styles.css`: protected v3/v4 design language plus v5 additive components.
- `schema.sql`: current schema contract.
- `scripts/reset-db.py`: development reset utility.
- `tests/test_app.py`: regression/security tests.

## Database groups
- Identity: `users`, `sessions`, `role_permissions`.
- Location: `campuses`, `buildings`, `floors`, `locker_rooms`, `lockers`.
- Workflows: `locker_requests`, `staff_requests`, `maintenance_records`.
- Audit/history: `audit_events`, `locker_events`, legacy `activity_log`.
- User events: `notifications`.

## Protected invariants
Student APIs must not serialize another student's name, ID, mobile, email, profile image or internal account identifier.
Role checks must use centralized permissions, not frontend flags.
Locker allocation must be protected by an immediate transaction and a current-state predicate.
History is append-oriented; current state is stored separately from historical events.
