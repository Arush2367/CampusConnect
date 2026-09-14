# Campus Connect — Audited Frontend + Product Implementation Plan

## 0. Goal

Transform the existing Campus Connect/CampusLock application into a consistent, polished
Campus Connect experience using the approved image assets while preserving the working
backend/API contracts wherever possible.

Primary rule:

> Do not rewrite working backend functionality merely to change the UI.

The redesign should make the application feel like one connected product rather than a
collection of independently styled screens.

---

## 1. Audit Summary

### Current strengths

- Authentication and role separation already exist.
- Backend authorization is server-side, not just frontend hiding.
- Locker workflows have explicit lifecycle/state handling and audit events.
- Notifications are persistent and user-scoped.
- Clubs already support membership, leadership, meetings, events and gallery memories.
- Events already support registration, custom forms and paid-event verification.
- Lost & Found already has matching/notification behavior.
- Problem reporting already exists.
- The frontend is a single-page application shell with route/view switching.
- CampusConnect-assets is now present and contains the approved visual direction.

### Important findings to fix before calling the build production-ready

#### A. Club member privacy leak — HIGH PRIORITY

`GET /api/clubs/<club_id>` currently returns the full member list including:

- full name
- student ID
- branch
- year

to any authenticated user who can open the club.

Recommended behavior:

- Normal students: public/minimal member display only.
- Club leader/co-leader: member management details.
- Authorized staff/admin: full operational details.

This should be fixed server-side, not only hidden in the frontend.

#### B. Event capacity is not enforced atomically — HIGH PRIORITY

The registration path accepts registrations but does not perform an atomic
capacity check/lock around the registration write.

Recommended behavior:

1. Begin transaction.
2. Count active registrations.
3. Reject when capacity is reached.
4. Insert/update registration.
5. Commit.

The frontend should show:

- available seats
- full state
- registration closed state

but the backend remains authoritative.

#### C. Gallery uploads need stronger server-side validation — MEDIUM PRIORITY

Club gallery uploads currently accept image payloads without the same explicit
validation discipline used by profile uploads.

Recommended behavior:

- validate data URI/MIME type server-side
- enforce a hard byte/character limit
- reject unsupported formats
- optionally validate decoded image dimensions
- record upload action in audit log

#### D. Test harness cleanup — MEDIUM PRIORITY

The repository contains a script-style `tests/test_app.py` rather than conventional
pytest/unittest test cases.

The existing script also assumes a particular seeded state and can fail with a
409 when a reused demo/test ID already exists.

Recommended behavior:

- make tests isolated and repeatable
- use a temporary/fresh database
- avoid hard-coded test IDs that collide with seed data
- make `pytest` discover real test functions/classes

#### E. Naming/documentation cleanup — LOW PRIORITY

Several backend/docs strings still say `Campus Buddy` or `CampusLock`.

These should be normalized to:

- Campus Connect — user-facing product name
- CampusLock — locker module only

Do not rename internal database/legacy identifiers unless necessary.

---

## 2. Todo Feature — Add This Next

The To-Do feature is a good addition because it is useful on the student dashboard
and naturally fits the Campus Connect value proposition.

### Student-facing MVP

Each task should support:

- title
- optional description
- due date
- priority: low / normal / high
- status: pending / completed
- created_at
- completed_at
- owner user_id

Optional source metadata:

- manual
- event
- club
- campus service

This allows a later version to create tasks from existing campus actions.

### Recommended API

- `GET /api/todos`
- `POST /api/todos`
- `PATCH /api/todos/<id>`
- `POST /api/todos/<id>/complete`
- `DELETE /api/todos/<id>`

### Recommended table

`todos`

- id
- user_id
- title
- description
- due_date
- priority
- status
- source_type
- source_id
- created_at
- completed_at

### UX

Dashboard:

- 3–5 most relevant tasks
- overdue indicator
- today's tasks
- quick add
- completed count

Dedicated page:

- Today
- Upcoming
- Completed
- Overdue

Do not overbuild reminders/calendar automation in the first pass.

---

## 3. Design System — Source of Truth

Use one shared design language everywhere.

### Brand palette

- Deep Navy / Slate — primary text, navigation, strong UI
- Terracotta — primary action/accent
- Dusty Rose — secondary highlight
- Warm Cream — page background
- Sage — positive/supportive accent
- Muted Gold — small emphasis/details
- Soft Blue-Gray — secondary surfaces
- Deep Plum — rare supporting accent

### Visual personality

- warm
- collegiate
- trustworthy
- modern
- human
- calm
- connected

Avoid:

- neon gradients
- generic purple SaaS gradients
- excessive glassmorphism
- heavy shadows
- childish cartoon styling
- random colors
- excessive decoration
- image-based UI controls

---

## 4. Layout Rules

### Desktop shell

```text
┌──────────────────────────────────────────────────────────────┐
│ Sidebar │ Header: search | notifications | profile          │
│         ├────────────────────────────────────────────────────┤
│         │ Page eyebrow                                      │
│         │ Page title + actions                              │
│         │                                                    │
│         │ Main content                                      │
│         │                                                    │
│         └────────────────────────────────────────────────────┤
└──────────────────────────────────────────────────────────────┘
```

### Sidebar

Order:

1. Dashboard
2. Events
3. Clubs & Societies
4. My Clubs
5. Campus Services
6. Lost & Found
7. Reports / Support
8. To-Do
9. Notifications
10. Requests
11. Profile

Staff/admin gets an operational version:

1. Operations
2. Events
3. Clubs
4. Problems
5. Lost & Found
6. Lockers
7. Requests
8. Students
9. Maintenance
10. Notifications
11. Audit
12. Profile

### Page anatomy

Every major page should follow:

1. page header
2. optional hero/banner
3. primary actions
4. filters/search
5. primary content
6. useful secondary content
7. intentional empty/loading/error state

### Card rules

- Use 1 consistent radius scale.
- Use 1 primary shadow.
- Use consistent internal padding.
- Avoid putting cards inside cards unless hierarchy truly requires it.
- Use image artwork only for visual sections; keep data-driven content as HTML.

---

## 5. Component Library to Build Before Redesigning Every Page

### Core UI

- Button: primary / secondary / ghost / danger
- Icon button
- Input
- Search input
- Textarea
- Select
- Checkbox
- Radio
- Toggle
- Date input
- File upload
- Badge
- Avatar

### Navigation

- Sidebar
- Top bar
- Mobile bottom navigation
- Tabs
- Breadcrumbs
- Pagination

### Content

- Panel
- Standard card
- Metric/stat card
- Event card
- Club card
- Service card
- Request card
- Notification row
- Table
- Timeline
- Empty state

### Feedback

- Toast
- Alert
- Modal
- Confirmation dialog
- Inline error
- Success message

### Loading

- text skeleton
- card skeleton
- table skeleton
- dashboard skeleton
- image skeleton
- button loading state
- page loading state

### Campus-specific

- Locker status
- Request status
- Event status
- Registration status
- Club membership status
- Problem priority/status
- To-Do priority/status

---

## 6. Approved Visual Asset Usage

### Use directly as assets

- logo
- login background
- dashboard hero
- clubs/events background
- 4 campus-service visuals
- empty-state illustrations
- success-state illustrations
- 404 artwork

### Do NOT bake into generated images

- live buttons
- forms
- navigation
- live names
- dates
- counts
- requests
- status values
- authentication controls

Those remain real HTML/CSS/JS.

### User-generated content

Club photos and event photos should remain user-uploadable.

Generated artwork is for:

- headers
- empty states
- service illustrations
- success states
- error states
- decorative backgrounds

---

## 7. Recommended Implementation Order

### Phase 1 — Protect functionality

1. Freeze backend/API behavior.
2. Run Ponytail architecture/scope review.
3. Fix privacy leak.
4. Fix event capacity race.
5. Harden gallery upload validation.
6. Clean the test harness.
7. Confirm all existing flows still work.

### Phase 2 — Design system

1. Add design tokens.
2. Add typography.
3. Add spacing/radius/shadow tokens.
4. Normalize buttons/forms/badges.
5. Build skeleton components.
6. Build shared cards/panels.
7. Build shared modal/toast/empty-state components.

### Phase 3 — Application shell

1. Sidebar.
2. Header/search.
3. Notification/profile area.
4. Mobile navigation.
5. Responsive breakpoints.
6. Route-to-navigation state.

### Phase 4 — Authentication

Use the generated login background directly.

Keep:

- real login form
- real role selector
- real signup form
- real auth messages

Do not recreate the artwork with SVG/CSS.

### Phase 5 — Student dashboard

Use the dashboard hero asset.

Sections:

- greeting
- quick actions
- upcoming events
- my schedule
- notifications
- To-Do
- campus services
- recommended clubs/events

### Phase 6 — To-Do

Implement the MVP API/database/UI.

Then connect dashboard quick actions and task completion.

### Phase 7 — Campus Services

Build the four services:

- Lockers
- Lost & Found
- Reports
- To-Do

Use the generated illustrations as visual accents/cards, not replacements for functional UI.

### Phase 8 — Clubs

Use:

- clubs/events background
- reusable club cards
- user-uploaded club images
- existing meetings/gallery/membership flows

Keep actual club images dynamic.

### Phase 9 — Events

Use:

- shared clubs/events visual system
- real event data
- real event images
- registration workflow
- capacity states

### Phase 10 — Staff/Admin

Build an action-oriented operations dashboard:

- pending actions
- urgent problems
- locker/maintenance status
- club/event approvals
- student requests
- operational metrics

### Phase 11 — States

Integrate:

- loading skeletons
- empty-state illustrations
- success illustrations
- error handling
- 404 page

### Phase 12 — Final quality pass

Test:

- desktop
- 1024px tablet
- 768px
- 390px
- 320px

Then audit:

- accessibility
- keyboard navigation
- contrast
- overflow
- performance
- console errors
- API errors
- permission boundaries

---

## 8. Claude + Ponytail Workflow

Never ask Claude to redesign the whole application in one request.

Use one controlled task at a time.

### Before each task

```text
Run Ponytail first.

Inspect the current architecture and affected routes/components.

Do not modify unrelated code.

Do not create a second component system if an existing reusable component
already performs the same job.
```

### Each implementation prompt should specify

- page/component
- intended UX
- assets to use
- APIs to preserve
- exact scope
- things explicitly forbidden
- validation to run afterward

### After each major task

Run:

- syntax/build check
- affected route check
- API smoke test
- Ponytail review
- git diff review

---

## 9. Performance Rules

Because the project will now contain many visual assets:

- prefer WebP/AVIF for large decorative artwork in production
- keep PNG only where transparency/quality requires it
- lazy-load below-the-fold images
- avoid using full 1536/2048px illustrations when a smaller image is sufficient
- do not load unused page artwork
- use responsive image sizes where practical
- avoid base64 for large production-scale media

The existing base64 image approach is acceptable for a hackathon demo, but should not
be treated as the long-term production storage strategy.

---

## 10. Definition of Done

The redesign is complete when:

- all current backend workflows still work
- To-Do works end-to-end
- no cross-user private-data leak remains
- event capacity cannot be exceeded by concurrent registrations
- upload validation exists server-side
- the UI uses one consistent design system
- approved Campus Connect assets are used directly
- skeleton/loading/empty/success/error states are consistent
- students and staff have clearly different operational views
- mobile navigation works
- no accidental legacy Campus Buddy branding remains in user-facing UI
- tests can run repeatedly against a clean database
