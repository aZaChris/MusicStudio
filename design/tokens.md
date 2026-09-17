# Design tokens (extracted from Claude Design artboards)

Source: `design/reference/MusicStudio.dc.html` (web) and `MusicStudio Mobile.dc.html` (app, future branch).

## Fonts
- Headings: `Poppins` (500/600/700)
- Body: `Nunito Sans` (400/600/700/800)

## Colors (OKLCH — warm coral/terracotta theme)
- Background (light): `oklch(97% 0.012 55)`
- Surface/card (light): `white` / `oklch(98% 0.008 55)`
- Border: `oklch(91% 0.015 55)`
- Text primary (light): `oklch(22% 0.02 40)`
- Text secondary (light): `oklch(48% 0.02 45)` / `oklch(50% 0.02 45)`
- Accent/brand (primary action, logo mark): `oklch(72% 0.16 55)` (warm coral)
- Success (paid / active): hue 150 — `oklch(38% 0.09 150)` text / `oklch(93% 0.06 150)` bg
- Danger (overdue / cancelled): hue 25 — `oklch(45% 0.16 25)` text / `oklch(93% 0.07 25)` bg
- Warning (low package / pending): hue 70-80 — `oklch(45% 0.11 70)` text / `oklch(94% 0.06 80)` bg

Dark theme: mirror the same hues, invert lightness (e.g. bg `oklch(22% 0.02 40)`, surface `oklch(27% 0.015 55)`, text `oklch(95% 0.01 55)`) — derive by flipping L, keep chroma/hue.

## Layout (web dashboard)
- Fixed left sidebar (232px): logo mark (♪ in coral rounded square) + nav (Dashboard, Studenti, Pagamenti) + studio name/email footer.
- Main content: max-width 1280px, 36/44px padding.
- Dashboard: header greeting + stat counters (active students, pending payments) → 1.6fr/1fr grid: weekly calendar (left) + upcoming/payments lists (right).
- Cards: white surface, 16px radius, 1px border, generous padding.
- Rounded corners throughout (10-16px), soft borders over shadows.

## Language
Artboard copy is in Italian ("Studenti", "Pagamenti", "pagamenti in sospeso", "Ciao, Anna 👋") — confirms IT is a first-class locale, not an afterthought. Build with i18n from the start (`react-i18next` or equivalent), EN + IT, default to browser locale.
