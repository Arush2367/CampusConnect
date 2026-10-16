# CampusConnect V21 Roadmap

## Baseline
V20 remains the protected baseline. This roadmap does not itself redesign existing features or change application behavior.

## Phase 0 â€” Protect the baseline
- Keep `main` untouched.
- Use `integration/v21` for integration work.
- Create one feature branch per major feature.
- Record current API, database, and UI contracts before implementation.
- Keep `.env`, credentials, and local/private data out of AI context and commits.

## Phase 1 â€” Shared foundation
- Keep the current HTML/CSS/JS architecture unless a specific need proves otherwise.
- Add only minimal module boundaries where they reduce merge conflicts.
- Reuse current RBAC and design tokens.
- Agree on database migration conventions and feature ownership.

## Phase 2 â€” Dark mode
- Extend the existing theme system instead of replacing it.
- Preserve CampusConnect brand colors, typography, spacing, and component layout.
- Use `Assets/loginpage_bg_darkmode.png` as the visual anchor if present.
- Ensure every new component works in light and dark mode.
- Do not regenerate existing artwork unless explicitly requested.

## Phase 3 â€” Library
Core scope: books, physical copies, availability, issue, return, reservations, student history, and staff management.
Defer fines, barcodes, and analytics until there is a demonstrated need.

## Phase 4 â€” Sports
Core scope: sports, facilities, teams/participants, registrations, schedules, and results. Avoid hardcoding one sport's rules into the platform.

## Phase 5 â€” Configurable exam seating engine
Flow: exam â†’ teacher-selected rule set â†’ rooms/seats â†’ allocation â†’ conflict report â†’ teacher approval â†’ final plan.
Separate hard constraints (never violated) from soft preferences (optimized when possible). Rules belong to each exam, not to one universal default. Never silently violate a hard constraint.

## Phase 6 â€” AI assistant
- Add a backend AI gateway and provider adapter.
- Never expose provider secrets in browser code.
- Start with general assistance; add campus tools only through explicit, permission-checked backend endpoints.
- Never give the model direct database access.
- Add request size/history limits, response caps, timeouts, and rate limits.

## Phase 7 â€” Controlled cross-feature integration
Expose only approved tools/endpoints to the assistant for events, library, sports, exam schedules, and notices.

## Phase 8 â€” Release validation
Regression-check auth/OTP, existing clubs/events, lockers, Lost & Found, problem reporting, notifications/audit, library, sports, exams, assistant, light/dark mode, and responsive layouts.

Do not merge to `main` until the relevant tests and review pass.