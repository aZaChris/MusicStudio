import { chromium } from "playwright";

const OUT = "/tmp/claude-1000/-home-christian-MusicStudio/b1f30b50-1fcd-43ff-98b7-39a4c1e33fd7/scratchpad";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 420, height: 900 } });
page.on("pageerror", (err) => console.log("[pageerror]", err.message));
page.on("console", (msg) => msg.type() === "error" && console.log("[console.error]", msg.text()));

async function loginAs(email, password) {
  await page.goto("http://localhost:8081/login", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1500);
  const inputs = await page.locator("input").all();
  await inputs[0].fill(email);
  await inputs[1].fill(password);
  await page.getByText("Log in", { exact: true }).click();
  await page.waitForTimeout(2500);
}

// Teacher: roster + payments tabs, student detail
await loginAs("owner@example.com", "password123");
await page.getByText("Students", { exact: true }).click();
await page.waitForTimeout(1500);
await page.screenshot({ path: `${OUT}/roster.png` });

// React Navigation keeps previous tab screens mounted (RN Web just hides
// them), so a getByText can match an off-screen duplicate — scope to the
// currently visible one. force:true because RN Web's absolutely-positioned
// scroll-container layers can shadow the text node for pointer-events
// purposes even though it's visually on top.
await page
  .getByText("Giulia Rossi", { exact: true })
  .locator("visible=true")
  .first()
  .click({ force: true });
await page.waitForTimeout(1500);
await page.screenshot({ path: `${OUT}/student-detail.png` });
console.log("student detail URL:", page.url());

await page.goBack();
await page.waitForTimeout(500);
await page.getByText("Payments", { exact: true }).first().click();
await page.waitForTimeout(1500);
await page.screenshot({ path: `${OUT}/payments.png` });

await browser.close();

// Parent portal in a fresh context
const browser2 = await chromium.launch();
const page2 = await browser2.newPage({ viewport: { width: 420, height: 900 } });
page2.on("pageerror", (err) => console.log("[parent pageerror]", err.message));

await page2.goto("http://localhost:8081/login", { waitUntil: "domcontentloaded" });
await page2.waitForTimeout(1500);
const inputs2 = await page2.locator("input").all();
await inputs2[0].fill("parent@example.com");
await inputs2[1].fill("password123");
await page2.getByText("Log in", { exact: true }).click();
await page2.waitForTimeout(2500);
console.log("parent URL:", page2.url());
await page2.screenshot({ path: `${OUT}/parent-portal.png` });
await browser2.close();

console.log("done");
