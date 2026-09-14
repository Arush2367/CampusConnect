# Campus Connect — Version 15 Changelog

## UI & Navigation
- Removed the duplicate top-navigation logo from the login screen because the supplied login background already contains the Campus Connect logo.
- Adjusted login artwork positioning so the embedded background logo remains visible.
- Added a structured Campus Actions card grid to the notice/announcement area.
- Restyled request and notification rows as compact action cards with the same structured visual language as To-Do items.

## Requests
- Student **Requests** now uses the unified request feed instead of showing only locker requests.
- Unified feed includes club proposals, club join requests, event payment requests, locker requests, Lost & Found reports, and campus problem reports.
- Student wording is consistently **My Requests**.

## Report Problem
- Added optional problem-photo upload with client-side compression.
- Reports submitted without a photo display a low-priority warning before submission and are stored with a low-priority notification.
- Problem listings can show the submitted photo.

## Lost & Found
- Students can remove their own Lost & Found reports.
- Dates accept either `YYYY-MM-DD` or `YY-MM-DD`; two-digit years are normalized to the 2000s.
- Pressing Enter in the date field normalizes the value before submission.

## To-Do
- Added optional repetition: daily, weekly, monthly, and custom.
- Weekly custom patterns support selected weekdays (e.g. Monday–Friday).
- Monthly custom patterns support selected months (e.g. January–March).
- Completing a repeating task automatically creates its next occurrence.
- Added optional motivation quotes displayed with tasks.

## Default Tester Accounts
- Admin: `ADMIN001` / `admin123`
- Student-1: `STU0001` / `123456789`
- Student-2: `STU0002` / `123456789`
- Startup migration repairs/creates these accounts even when the bundled database is already populated.

## Version 15.1 — Unified Modal Card UI + Login Artwork
- Standardized modal/card appearance to match the polished Report Item reference.
- Upgraded Propose a New Club, Post a Notice, Assign Role, and Create Event forms to the shared modal-form structure.
- Increased modal width, spacing, rounded corners, input height, and footer-button consistency.
- Lifted login artwork upward so the background begins at the top of the page and reduced its opacity.
- Added the modal/card standard to Project_rules.md for future UI work.

- v15.2: Increased login background artwork visibility by 80% relative to v15.1 (opacity 0.23 → 0.414), while preserving the top-aligned artwork position and foreground readability.

- v15.3: Login background artwork opacity is now set to 0.75, per requested visual tuning. Top alignment and existing foreground UI are unchanged.
