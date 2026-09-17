import { chromium } from "playwright";

const OUT = "/tmp/claude-1000/-home-christian-MusicStudio/b1f30b50-1fcd-43ff-98b7-39a4c1e33fd7/scratchpad";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 420, height: 900 } });

page.on("console", (msg) => {
  if (msg.type() === "error") console.log("[console.error]", msg.text());
});
page.on("pageerror", (err) => console.log("[pageerror]", err.message));

// Metro's dev client keeps a live WebSocket open for HMR, so "networkidle"
// never fires — use domcontentloaded + a fixed settle wait instead.
await page.goto("http://localhost:8081", { waitUntil: "domcontentloaded", timeout: 30000 });
await page.waitForTimeout(4000);

await page.fill('input[type="text"], input:below(:text("Email"))', "owner@example.com").catch(() => {});
// Fallback: fill by order since RN Web inputs may not carry type="email"
const inputs = await page.locator("input").all();
if (inputs.length >= 2) {
  await inputs[0].fill("owner@example.com");
  await inputs[1].fill("password123");
} else {
  console.log("Could not find 2 inputs, found:", inputs.length);
}

await page.screenshot({ path: `${OUT}/mobile-login-filled.png` });

await page.getByText("Log in", { exact: true }).click();
await page.waitForTimeout(3000);
await page.screenshot({ path: `${OUT}/mobile-after-login.png` });

console.log("URL after login:", page.url());

await browser.close();
