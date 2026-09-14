# CampusLock — Project Rules

## 1. CHANGE CONTROL
Only modify files, functions, components, styles, database tables, or behavior explicitly required by the current task.

Do NOT make unrelated improvements.
Do NOT refactor unrelated code.
Do NOT redesign existing UI unless explicitly requested.
Do NOT rename existing IDs, classes, functions, routes, database fields, or files unless explicitly required.

## 2. GUI / PRODUCT LANGUAGE INVARIANT
The v3/v4 visual language is protected. New components must use the existing tokens, spacing rhythm, typography, radii, status treatment, and interaction language.
A complete redesign is forbidden unless explicitly requested.

## 3. FEATURE MODIFICATION
1. Inspect first.
2. Define the smallest affected surface.
3. Patch modularly.
4. Preserve all unrelated behavior.
5. Preserve demo credentials and valid data unless migration is explicitly required.

## 4. SECURITY INVARIANT
Never implement security only in JavaScript. Every authentication, authorization, privacy, state-transition and sensitive-data rule must be enforced server-side.

## 5. BACKWARD COMPATIBILITY
The latest explicitly user-approved stable version is the baseline.
Previous stable packages must remain recoverable.
Migrations must preserve valid data and the demo credentials `STU1001` and `ADMIN001` unless the user explicitly changes them.

## 6. TEST / REGRESSION RULE
After every material change, run:
- Python syntax validation
- JavaScript syntax validation
- database migration/seed validation
- changed API smoke tests
- authorization/privacy/security invariant tests
- relevant frontend regression checks

Fix failures before packaging.

## 7. AI WORKFLOW LOOP — MANDATORY
Every AI working on this repository MUST treat the following as a continuous loop:

**READ RULES → READ CURRENT CONTEXT → DEFINE SCOPE → INSPECT → PATCH MINIMALLY → TEST → REGRESSION CHECK → UPDATE CONTEXT → VERSION/PACKAGE → STOP**

Before editing:
- Read this file completely.
- Read `README.md` current stable baseline, architecture, feature state, security invariants, modification history and remaining roadmap.
- Inspect the exact files, routes, database tables, permissions and UI components involved.
- Write down internally what is allowed to change and what must remain frozen.

While editing:
- Touch the smallest required file/function set.
- Do not remove working behavior merely because a different architecture looks cleaner.
- Do not silently change demo credentials.
- Do not silently replace or delete the user's database.
- Do not duplicate routes, tables or business rules.
- Do not log passwords, password hashes, raw sessions or private student data into public-facing responses or audit messages.

After editing:
- Run syntax checks.
- Run migrations/seed checks.
- Run API smoke tests.
- Run RBAC/privacy/security tests.
- Run the regression suite.
- Update this file and `README.md` with every material architectural, database, API, security or UI change.
- Package the next version without overwriting the previous stable package.

## 8. AUTHORIZATION MODEL
The authoritative application roles are:
- `super_admin`
- `locker_manager`
- `staff`
- `student`

Permissions are defined centrally in `server.py` and mirrored by the UI only for presentation. Server-side permission checks are mandatory.

## 9. PRIVACY MODEL
Students may see locker availability and their own locker/request information.
Private data about another student must never be returned by a student-authorized endpoint, even when the frontend is bypassed.
Staff and administrators receive private student information only where their permission grants it.

## 10. REQUEST STATE MACHINE
Valid request transitions include:
- `pending → approved → assigned`
- `pending → rejected`
- `pending → cancelled`
- `pending → expired`
- `approved → cancelled` only where business rules permit it.

Invalid transitions must be rejected server-side. Each transition is audited.

## 11. MAINTENANCE STATE MACHINE
Valid maintenance lifecycle:
- `reported → acknowledged → in_repair → resolved → available`

A maintained locker must not be treated as normally available/occupied simultaneously; entering maintenance cancels pending requests for that locker.

## 12. LOCKER IDENTITY
Human-readable display codes remain in the format:
- `A1-001` = Ground Floor, Group 1, Locker 001
- `B1-001` = First Floor, Group 1, Locker 001
- `C1-001` = Second Floor, Group 1, Locker 001
- `D1-001` = Third Floor, Group 1, Locker 001

Stable internal IDs remain separate from display codes.

## 13. DEMO / DEVELOPMENT BASELINE
The following credentials are protected test fixtures:
- Student: `STU1001 / student123`
- Primary administrator: `ADMIN001 / admin123`

Do not modify them except by explicit instruction.

## 14. STARTUP RULE
Use:
`py server.py`
then open:
`http://localhost:3000`

Do not double-click `index.html` as the application server.

## 15. CONTEXT / HANDOFF REQUIREMENT
A future AI must be able to continue from the repository without hidden conversation memory. Therefore `README.md`, `Project_rules.md`, and `PROJECT_STATE.md` must record current state, architecture, route inventory, permission matrix, feature matrix, security invariants, protected functionality, known limitations, tests, and modification history.

## 16. NO OPPORTUNISTIC WORK
No "while I'm here" redesigns, dependency swaps, renames, UI rewrites, or unrelated fixes. Only the current requested scope and changes strictly required for correctness/safety are allowed. Before packaging, the AI must read `PROJECT_STATE.md` and update it with objective, files changed, database/API changes, UI changes, tests executed, regressions checked, known limitations, and untouched areas.

## UI Standard — v15.1 onward
All new and revised modal cards/forms must follow the established Campus Connect modal card language: large rounded cream-white container, clear title row with a rounded close button, uppercase field labels, generous spacing, large rounded inputs, two-column form grids on desktop, and aligned rounded footer actions. Do not introduce raw/default browser form styling when an equivalent shared modal style exists. Reuse the shared `.modal`, `.modal-head`, `.modal-form`, `.form-grid`, and `.modal-actions` patterns.

The landing/login artwork must begin at the top edge of the screen and remain a subtle background layer behind the navigation and authentication card.
