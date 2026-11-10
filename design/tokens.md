# Design tokens

The visual language lives in `design/system/` (exported from the "MusicStudio" design system on
claude.ai, 2026-11-10): `tokens.json` is the source, `README.md` the brand book, `motion.md` the
animations. `npm run tokens` generates `src/constants/tokens.generated.ts` from it, and
`src/constants/theme.ts` re-exports it with the fonts and text styles React Native needs.

`design/reference/` holds the earlier Poppins/Nunito artboards and is kept only as history.
The review of the system and the list of deviations is in `docs/design-system-review.md`.
