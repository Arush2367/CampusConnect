# Campus Connect — Version 12 Changelog

## Visual / responsive fixes
- Replaced sidebar/navigation emoji icons with the approved `CampusConnect-assets/icons` icon system.
- Cropped icon assets are now clipped into circular visual containers so square source canvases do not appear as pasted rectangles.
- Added consistent icon sizing, padding, borders, and alignment across sidebar, quick actions, auth role controls, SSO buttons, service tiles, and status areas.
- Removed the desktop mobile-bottom navigation bar; the sidebar remains the primary desktop navigation.
- Fixed sidebar labels being visually clipped by wrapping navigation text in dedicated labels with responsive flex sizing.
- Added safer card text wrapping and min-width rules to prevent headings, descriptions, badges, and action controls from escaping their cards.
- Added responsive admin dashboard layouts for desktop, tablet, and mobile widths.

## Authentication / login
- Redesigned login identifier/password controls with circular icon treatment and clearer typography.
- Added readable text-overlay treatment over the login artwork without adding a separate decorative text card.
- SSO provider buttons now use the approved provider icon assets.
- Existing student login and new-account login verified through the API.

## Admin experience
- Replaced the locker-centric admin dashboard with a Campus Connect Operations Center.
- Added action-center cards for requests, maintenance, events, clubs, students, and audit activity.
- Added operational focus panel and campus visual context.

## Additional fixes
- Updated event/meeting mode visuals to use icon assets rather than emoji glyphs.
- Made user avatars circular for consistency.
- Preserved backend APIs and existing workflows while improving frontend presentation.

## Validation
- `node --check public/app.js` passes.
- Python compilation passes for server/backend modules.
- Existing integration test script was made repeatable with unique test IDs.
- `python tests/test_app.py` finishes with `ALL_TESTS_PASSED`.
- Existing student login verified.
- New student signup followed by login verified.
- New `CampusConnect-assets/icons` static icons and existing Campus Connect artwork return HTTP 200 from the local server.

## Known limitation
- The To-Do system is still frontend/local-storage based; database/API persistence can be added in the next backend phase.
