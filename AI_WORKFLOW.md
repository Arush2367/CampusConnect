# CampusConnect V21 â€” AI Engineering Workflow

## Purpose
This file is the handoff contract for every AI agent working on CampusConnect V21. The stable `main` branch is never edited directly.

## Branch policy
- `main` = protected production/stable baseline.
- `integration/v21` = integration branch for the current upgrade.
- `feature/<name>` = one feature at a time.
- Never commit directly to `main`.
- Never force-push shared branches.
- Merge only after local tests and review pass.

Recommended feature branches:
- `feature/dark-mode`
- `feature/library`
- `feature/sports`
- `feature/exam-seating`
- `feature/ai-assistant`

## AI roles
- **Architect/reviewer:** ChatGPT for architecture, contracts, security review, test plans, and diff review.
- **Implementation:** Claude or Antigravity for focused changes in the assigned feature branch.
- **Verification:** VS Code/local Python and browser testing as the final source of truth.

## Token rules
1. Do not paste the entire repository into an AI prompt.
2. Read `Project_rules.md` (if present), `PROJECT_STATE.md`, and the feature contract first.
3. Give an agent only the files needed for its current task.
4. Prefer diffs and exact files over repeated full-file context.
5. Never rewrite a working module when a small patch is sufficient.
6. Keep handoff state in repository files, not only in chat memory.
7. Summarize completed work before handing a branch to another AI.

## Secret rules
Never send these to an AI:
- `.env`
- production credentials or database passwords
- session secrets
- SMTP credentials
- real student/private data

## Scope rules
Before editing, an agent must identify:
- exact files allowed to change
- exact behavior being added
- database tables affected
- API routes affected
- roles/permissions affected
- UI surfaces affected

No unrelated refactoring, dependency swaps, renaming, redesign, or cleanup.

## Handoff format
```text
TASK:
BRANCH:
FILES CHANGED:
DATABASE CHANGES:
API CHANGES:
UI CHANGES:
TESTS RUN:
KNOWN LIMITATIONS:
NEXT STEP:
```

## Required loop
READ RULES â†’ READ STATE â†’ DEFINE SCOPE â†’ INSPECT â†’ PATCH MINIMALLY â†’ TEST â†’ REGRESSION CHECK â†’ UPDATE STATE â†’ HANDOFF

## Review rule
Review the Git diff, not only the rendered page. A feature is not complete just because the UI appears to work.

## Integration rule
Feature branch â†’ review â†’ `integration/v21` â†’ full regression â†’ release candidate â†’ `main`.