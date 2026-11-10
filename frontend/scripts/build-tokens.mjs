// Generates src/theme/tokens.css from the design system's tokens.json (single source of truth).
// Run: npm run tokens   (also copies the ms-* component kit into src/theme/)
import { copyFileSync, readFileSync, writeFileSync } from 'node:fs'

const src = new URL('../../design/system/tokens.json', import.meta.url)
const out = new URL('../src/theme/tokens.css', import.meta.url)
const t = JSON.parse(readFileSync(src, 'utf8'))

const themes = t.color.themes.map((x) => x.id) // first one is the default
const pick = (value, theme) => (typeof value === 'string' ? value : (value[theme] ?? value[themes[0]]))

const vars = (theme) => {
  const lines = []
  for (const tok of t.color.tokens) lines.push(`  --${tok.name}: ${pick(tok.value, theme)};`)
  for (const tok of t.shadow.tokens) lines.push(`  --${tok.name}: ${pick(tok.value, theme)};`)
  return lines.join('\n')
}

const fixed = []
for (const [name, value] of Object.entries(t.type.families)) fixed.push(`  --font-${name}: ${value};`)
for (const family of ['spacing', 'radius', 'duration', 'easing'])
  for (const tok of t[family].tokens) fixed.push(`  --${tok.name}: ${tok.value};`)

const css = `/* Generated from design/system/tokens.json by scripts/build-tokens.mjs. Do not edit by hand. */
:root,
:root[data-theme='${themes[0]}'] {
${vars(themes[0])}
${fixed.join('\n')}
}

${themes
  .slice(1)
  .map((id) => `:root[data-theme='${id}'] {\n${vars(id)}\n}`)
  .join('\n\n')}
`
writeFileSync(out, css)
// The component kit (ms-* classes) lives next to the tokens; the Docker build only sees frontend/.
copyFileSync(
  new URL('../../design/system/components.css', import.meta.url),
  new URL('../src/theme/components.css', import.meta.url),
)
console.log(`tokens.css: ${t.color.tokens.length} colours, ${themes.length} themes`)
