# Campus Connect — Version 18 Changelog

## Fixes and improvements
- Auth landing navigation: About and Contact now scroll to real, styled sections; Home, Features and Get Started behavior remain intact.
- Admin operations dashboard: removed the old Review Queue action from the greeting card and moved request review into the Action Center / Operational Focus while refreshing the greeting into the Campus Connect card style.
- To-Do: fixed the repetition control path and task persistence so Add Task works for both students and staff/admin users; task storage is now user-scoped with legacy-task migration.
- To-Do: restored the missing custom weekly/monthly repeat selector required by the existing repetition logic.
- Clubs: fixed the staff/admin club-list query that referenced a non-existent `clubs.event_mode` column and caused the Clubs screen to fail for staff/admin users.
- Kept the existing single `public/CampusConnect-assets` asset tree; no duplicate project/asset folders were added.

## Verification
- Python compilation: passed
- JavaScript syntax check: passed
- Existing end-to-end integration suite (`CAMPUSCONNECT_EMAIL_MODE=test`): `ALL_TESTS_PASSED`
- Admin `/api/clubs`: HTTP 200 verified
- Student `/api/clubs`: HTTP 200 verified
- No duplicate function declarations detected in `public/app.js`
- No legacy `assets 2` / `assets2` paths remain
