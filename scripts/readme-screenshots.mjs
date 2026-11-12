// README screenshots of the portal, light and dark. Needs the API on :8000 with seed_demo
// data (started with THROTTLE_LOGIN=100/min: the script logs in 6 times) and the SPA on :5173.
// Run from frontend/:
//   node ../scripts/readme-screenshots.mjs ../docs/assets/screenshots
// It also writes the phone shots of the landing's gallery to frontend/public/showcase/ (Italian UI).
import { chromium } from "playwright";

const OUT = process.argv[2];
const BASE = "http://localhost:5173";
const browser = await chromium.launch();

async function session(theme, viewport, email, locale = "en-US") {
  const ctx = await browser.newContext({
    viewport,
    colorScheme: theme,
    locale,
    deviceScaleFactor: 1.5,
  });
  const page = await ctx.newPage();
  if (email) {
    await page.goto(BASE + "/login");
    await page.locator("input[type=email]").fill(email);
    await page.locator("input[type=password]").fill("password123");
    await page.locator("button[type=submit]").click();
    await page.waitForURL((u) => !u.pathname.startsWith("/login"));
  }
  return { ctx, page };
}

async function shot(page, path, name, { toMain = false } = {}) {
  if (path) await page.goto(BASE + path);
  await page.waitForLoadState("networkidle");
  await page
    .waitForFunction(
      () => !/Caricamento…|Loading…/.test(document.body.innerText),
      null,
      { timeout: 15000 },
    )
    .catch(() =>
      console.warn(`${name}: still loading after 15 s, shot taken anyway`),
    );
  await page.evaluate(() => document.fonts.ready);
  // A client-side navigation keeps the old scroll. On a phone the staff menu sits above the
  // page, so the gallery shots scroll to the content itself.
  await page.evaluate((toMain) => {
    window.scrollTo(0, 0);
    if (toMain) document.querySelector("main")?.scrollIntoView();
  }, toMain);
  await page.waitForTimeout(600); // let entry animations settle
  await page.screenshot({
    path: name.includes("/") ? name : `${OUT}/${name}.png`,
    quality: name.endsWith(".jpg") ? 82 : undefined,
  });
  console.log(name, page.url());
}

const desktop = { width: 1440, height: 820 };
for (const theme of ["light", "dark"]) {
  const anon = await session(theme, desktop);
  await shot(anon.page, "/", `landing-${theme}`);
  await anon.ctx.close();

  const { ctx, page } = await session(theme, desktop, "owner@example.com");
  await shot(page, "/", `home-${theme}`);
  await page.getByRole("link", { name: "Students", exact: true }).click();
  await page.locator('a[href^="/students/"]').first().click();
  await shot(page, null, `student-${theme}`);
  await ctx.close();

  const parent = await session(theme, desktop, "parent@example.com");
  await shot(parent.page, "/", `parent-${theme}`);
  await parent.ctx.close();

  const phone = await session(
    theme,
    { width: 390, height: 844 },
    "owner@example.com",
  );
  await shot(phone.page, "/", `home-mobile-${theme}`);
  await phone.ctx.close();

  // Landing gallery: the same pages a teacher and a parent use on the phone.
  const SHOWCASE = "public/showcase";
  const iphone = { width: 390, height: 844 };
  const owner = await session(theme, iphone, "owner@example.com", "it-IT");
  await shot(owner.page, "/", `${SHOWCASE}/home-${theme}.jpg`, {
    toMain: true,
  });
  await owner.page.goto(BASE + "/students");
  await owner.page.locator('a[href^="/students/"]').first().click();
  await shot(owner.page, null, `${SHOWCASE}/student-${theme}.jpg`, {
    toMain: true,
  });
  await shot(owner.page, "/payments", `${SHOWCASE}/payments-${theme}.jpg`, {
    toMain: true,
  });
  await owner.ctx.close();
  const family = await session(theme, iphone, "parent@example.com", "it-IT");
  await shot(family.page, "/", `${SHOWCASE}/parent-${theme}.jpg`);
  await family.ctx.close();
}
await browser.close();
