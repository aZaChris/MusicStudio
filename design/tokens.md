# Design tokens

The visual language lives in `design/system/` (exported from the "MusicStudio" design system on
claude.ai, 2026-11-10):

- `tokens.json` — the single source of truth (colours for light and dark, type, spacing, radii,
  shadows, motion).
- `README.md` — the brand book: voice, colour rules, shapes, the "beats" motif, accessibility.
- `motion.md` — the six animations and the reduced-motion rule.
- `components.css` — the `ms-*` CSS kit.

`frontend/src/theme/tokens.css` and `frontend/src/theme/components.css` are generated from these
files: run `npm run tokens` in `frontend/` after changing them. The earlier Poppins/Nunito
artboards were removed from the tree on 2026-11-12; git history still has them (`design/reference/`).
