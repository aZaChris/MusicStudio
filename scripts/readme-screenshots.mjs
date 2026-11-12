// README screenshots of the portal, light and dark. Needs the API on :8000 with seed_demo
// data (started with THROTTLE_LOGIN=100/min: the script logs in 6 times) and the SPA on :5173.
// Run from frontend/:
//   node ../scripts/readme-screenshots.mjs ../docs/assets/screenshots
import { chromium } from 'playwright'

const OUT = process.argv[2]
const BASE = 'http://localhost:5173'
const browser = await chromium.launch()

async function session(theme, viewport, email) {
  const ctx = await browser.newContext({ viewport, colorScheme: theme, locale: 'en-US', deviceScaleFactor: 1.5 })
  const page = await ctx.newPage()
  if (email) {
    await page.goto(BASE + '/login')
    await page.locator('input[type=email]').fill(email)
    await page.locator('input[type=password]').fill('password123')
    await page.locator('button[type=submit]').click()
    await page.waitForURL((u) => !u.pathname.startsWith('/login'))
  }
  return { ctx, page }
}

async function shot(page, path, name) {
  if (path) await page.goto(BASE + path)
  await page.waitForLoadState('networkidle')
  await page.evaluate(() => document.fonts.ready)
  await page.waitForTimeout(600) // let entry animations settle
  await page.screenshot({ path: `${OUT}/${name}.png` })
  console.log(name, page.url())
}

const desktop = { width: 1440, height: 820 }
for (const theme of ['light', 'dark']) {
  const anon = await session(theme, desktop)
  await shot(anon.page, '/', `landing-${theme}`)
  await anon.ctx.close()

  const { ctx, page } = await session(theme, desktop, 'owner@example.com')
  await shot(page, '/', `home-${theme}`)
  await page.getByRole('link', { name: 'Students', exact: true }).click()
  await page.locator('a[href^="/students/"]').first().click()
  await shot(page, null, `student-${theme}`)
  await ctx.close()

  const parent = await session(theme, desktop, 'parent@example.com')
  await shot(parent.page, '/', `parent-${theme}`)
  await parent.ctx.close()

  const phone = await session(theme, { width: 390, height: 844 }, 'owner@example.com')
  await shot(phone.page, '/', `home-mobile-${theme}`)
  await phone.ctx.close()
}
await browser.close()
