// Renders an SVG or an HTML page to PNG with Playwright's Chromium (run from frontend/).
// Usage: node ../scripts/render-png.mjs <input.svg|html> <out.png> <width> <height>
import { chromium } from 'playwright'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const [input, out, w, h] = process.argv.slice(2)
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: +w, height: +h } })
if (input.endsWith('.svg')) {
  const svg = readFileSync(input, 'utf8')
  await page.setContent(`<style>html,body{margin:0;background:transparent}svg{width:${w}px;height:${h}px;display:block}</style>${svg}`)
} else {
  await page.goto('file://' + resolve(input))
}
await page.evaluate(() => document.fonts.ready)
await page.screenshot({ path: out, omitBackground: true })
await browser.close()
