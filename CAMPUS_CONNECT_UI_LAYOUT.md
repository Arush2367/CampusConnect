# Campus Connect — UI Layout & Consistency Rules

## Brand
Campus Connect — People · Ideas · Opportunities

## Visual language
Warm, collegiate, trustworthy, human, modern, calm.

### Palette
- Ink/Navy: `#24364B`
- Terracotta: `#B96550`
- Dusty Rose: `#C68F87`
- Warm Cream: `#F7F2E9`
- Sage: `#788875`
- Muted Gold: `#C7A66A`
- Soft Blue: `#A9BBC8`
- Deep Plum: `#5E4C61`

## Layout
- Desktop: fixed 256px sidebar + flexible content area.
- Mobile: compact top bar + mobile bottom navigation.
- Main content max width: 1400px.
- Page padding: 32px desktop, 20px mobile.
- Prefer two-column layouts for related content and single-column layouts for focus workflows.

## Page anatomy
Every page should use:
1. Eyebrow / context label.
2. Page title.
3. Primary action(s).
4. Optional filter/search row.
5. Main content.
6. Intentional loading, empty, success and error states.

## Cards
- Standard radius: 16px; hero radius: 24–28px.
- Border: 1px `var(--line)`.
- Shadow: soft, never heavy.
- Padding: 16–24px.
- Avoid nested cards unless hierarchy is necessary.

## Buttons
- Primary: terracotta.
- Secondary: white/cream with border.
- Danger: semantic red.
- Radius: 12px or pill only for prominent CTA buttons.
- Every interactive control needs hover/focus/disabled states.

## Typography
Use a clean sans-serif for UI and a restrained serif for major editorial headings.
Avoid excessive font weights and all-caps body copy.

## Images
Generated artwork is used directly as image assets. Do not redraw artwork with CSS,
SVG or canvas. Functional UI always remains HTML/CSS/JS.

## Data-driven media
Club and event images are user-provided and must remain dynamic. Do not replace them
with generated artwork.

## States
Every data-driven view needs:
- loading skeleton
- empty state
- error state
- success feedback where an action changes state

## Accessibility
- Keyboard reachable controls.
- Visible focus rings.
- Semantic labels.
- No information conveyed by color alone.
- Minimum touch-friendly target sizes on mobile.

## Responsive breakpoints
- 1200px: compact content grid.
- 900px: collapse secondary columns and hide desktop search if necessary.
- 700px: mobile navigation and stacked hero/cards.
- 390px: compact spacing and full-width primary actions.
