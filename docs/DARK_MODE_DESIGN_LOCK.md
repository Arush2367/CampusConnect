# CampusConnect Dark Mode Design Lock

## Reference asset
`Assets/loginpage_bg_darkmode.png`

Use this as the visual anchor for the V21 dark-mode direction if the asset is present.

## Preserve
- CampusConnect logo artwork and proportions
- existing page composition
- typography hierarchy
- current spacing and radius language
- warm brand accents
- navy/deep-blue night atmosphere
- warm architectural lighting
- subtle, premium contrast rather than pure-black UI

## Avoid
- generic black/purple cyberpunk styling
- changing the light-mode visual identity
- random accent colors per page
- changing artwork composition just to create a dark variant
- excessive glow, blur, gradients, or neon effects

## Asset generation rule
A dark asset should keep the light asset's canvas dimensions, subject placement, crop, logo placement, and visual style. Prefer changing lighting, background tone, shadows, and contrast only, unless a new composition is explicitly requested.

## Implementation rule
Prefer the existing CSS variables/theme system. New components must use shared tokens rather than embedding unrelated dark colors throughout component styles.