// Generates src/constants/tokens.generated.ts from the design system's tokens.json.
// Run: npm run tokens
import { readFileSync, writeFileSync } from "node:fs";

const t = JSON.parse(readFileSync(new URL("../design/system/tokens.json", import.meta.url), "utf8"));
const camel = (name) => name.replace(/-([a-z0-9])/g, (_, c) => c.toUpperCase());
const themes = t.color.themes.map((x) => x.id);
const pick = (value, theme) => (typeof value === "string" ? value : (value[theme] ?? value[themes[0]]));
const px = (v) => Number.parseFloat(v);

const colors = Object.fromEntries(
  themes.map((theme) => [theme, Object.fromEntries(t.color.tokens.map((tok) => [camel(tok.name), pick(tok.value, theme)]))]),
);
const scale = (family, prefix) =>
  Object.fromEntries(t[family].tokens.map((tok) => [camel(tok.name.replace(prefix, "")), px(tok.value)]));
const easing = Object.fromEntries(
  t.easing.tokens.map((tok) => [
    camel(tok.name.replace("ease-", "")),
    tok.value.match(/cubic-bezier\(([^)]+)\)/)[1].split(",").map(Number),
  ]),
);

const out = `// Generated from design/system/tokens.json by scripts/build-theme.mjs. Do not edit by hand.
export const Colors = ${JSON.stringify(colors, null, 2)} as const;

export const Space = ${JSON.stringify(scale("spacing", "space-"), null, 2)} as const;

export const Radii = ${JSON.stringify(scale("radius", "radius-"), null, 2)} as const;

export const Duration = ${JSON.stringify(scale("duration", "duration-"), null, 2)} as const;

/** Cubic-bezier control points, ready for reanimated's Easing.bezier(...). */
export const Curves = ${JSON.stringify(easing, null, 2)} as const;
`;
writeFileSync(new URL("../src/constants/tokens.generated.ts", import.meta.url), out);
console.log(`tokens.generated.ts: ${t.color.tokens.length} colours, ${themes.length} themes`);
