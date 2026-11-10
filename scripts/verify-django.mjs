#!/usr/bin/env node
// End-to-end check of the exported web build against a real local Django backend (T027).
//
// Prerequisites (see specs/002-django-api-parity/quickstart.md):
//   backend: dev settings, `seed_demo` data, CORS_ALLOWED_ORIGINS=http://localhost:8081, :8000
//   app:     EXPO_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1 npx expo export --platform web
//            npx expo serve --port 8081
// Usage: node scripts/verify-django.mjs [screenshot-dir]
// Prints PASS/FAIL per step; exit code 1 if any step fails.
import { chromium } from "playwright";

const APP = process.env.APP_URL ?? "http://localhost:8081";
const API = process.env.API_URL ?? "http://127.0.0.1:8000/api/v1";
const SHOTS = process.argv[2];
const PASSWORD = "password123";

const results = [];
async function step(name, fn) {
  try {
    await fn();
    results.push(["PASS", name]);
    console.log(`PASS  ${name}`);
  } catch (error) {
    results.push(["FAIL", name]);
    console.log(`FAIL  ${name}\n      ${String(error.message ?? error).split("\n")[0]}`);
  }
}
const expect = (ok, message) => {
  if (!ok) throw new Error(message);
};

async function api(path, { token, method = "GET", body } = {}) {
  const res = await fetch(API + path, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  return { status: res.status, body: await res.json().catch(() => null) };
}
async function tokenFor(email) {
  const { body } = await api("/auth/token/", { method: "POST", body: { email, password: PASSWORD } });
  return body.access;
}
const pad = (n) => String(n).padStart(2, "0");
const today = () => {
  const d = new Date();
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 420, height: 900 }, locale: "en-GB" });
const page = await context.newPage();
const consoleErrors = [];
page.on("pageerror", (err) => consoleErrors.push(err.message));
const shot = async (name) => SHOTS && page.screenshot({ path: `${SHOTS}/${name}.png` });

async function login(email) {
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Log in" }).click();
}

const ownerToken = await tokenFor("owner@example.com");
const before = (await api("/dashboard/", { token: ownerToken })).body;

await step("opens on the login screen without a session", async () => {
  await page.goto(APP, { waitUntil: "domcontentloaded" });
  await page.getByLabel("Email").waitFor({ timeout: 20000 });
  await shot("01-login");
});

await step("wrong password shows 'Invalid email or password.'", async () => {
  await page.getByLabel("Email").fill("owner@example.com");
  await page.getByLabel("Password").fill("wrong");
  await page.getByRole("button", { name: "Log in" }).click();
  await page.getByText("Invalid email or password.").waitFor({ timeout: 10000 });
});

await step("owner signs in and sees the server's dashboard counts", async () => {
  await login("owner@example.com");
  await page.getByText("Hi, owner 👋").waitFor({ timeout: 15000 });
  await page.getByText(String(before.active_students_count), { exact: true }).first().waitFor();
  await page.getByText(String(before.pending_payments_count), { exact: true }).first().waitFor();
  await shot("02-home");
});

const upcoming = before.upcoming.find((l) => l.status === "scheduled");
await step("completing a lesson with a note updates the server and the home", async () => {
  expect(upcoming, "seed has no scheduled upcoming lesson for the owner");
  const pkgBefore = upcoming.package
    ? (await api(`/packages/${upcoming.package}/`, { token: ownerToken })).body.lessons_remaining
    : null;
  await page.getByRole("button", { name: new RegExp(upcoming.student_name) }).first().click();
  await page.getByLabel("Progress note").fill("E2E: scales in G major");
  await shot("03-complete-dialog");
  await page.getByRole("button", { name: "Mark complete" }).click();
  await page.getByRole("button", { name: "Mark complete" }).waitFor({ state: "detached", timeout: 10000 });
  const lessons = (await api(`/students/${upcoming.student}/lessons/`, { token: ownerToken })).body;
  const done = lessons.find((l) => l.id === upcoming.id);
  expect(done.status === "completed", `lesson status is ${done.status}`);
  expect(done.notes === "E2E: scales in G major", "note not saved");
  if (pkgBefore !== null) {
    const pkgAfter = (await api(`/packages/${upcoming.package}/`, { token: ownerToken })).body.lessons_remaining;
    expect(pkgAfter === pkgBefore - 1, `package ${pkgBefore} -> ${pkgAfter}`);
  }
});

await step("roster lists students and the detail shows the completed lesson with its note", async () => {
  await page.getByRole("tab", { name: /Students/ }).click();
  const name = (await api(`/students/${upcoming.student}/`, { token: ownerToken })).body.full_name;
  await page.getByRole("button", { name }).click();
  await page.getByText("E2E: scales in G major").waitFor({ timeout: 10000 });
  await page.getByText("Completed", { exact: true }).first().waitFor();
  await shot("04-student-detail");
});

await step("a cash payment is registered with today's local date", async () => {
  await page.getByRole("tab", { name: /Payments/ }).click();
  const students = (await api("/students/?is_active=true", { token: ownerToken })).body.results;
  const target = students[0];
  await page.getByRole("radio", { name: target.full_name }).click();
  await page.getByLabel("Amount").fill("42,50");
  await page.getByRole("radio", { name: "Cash" }).click();
  await page.getByRole("button", { name: "Register payment" }).click();
  await page.getByText("Payment registered.").waitFor({ timeout: 10000 });
  const payments = (await api(`/payments/?student=${target.id}`, { token: ownerToken })).body.results;
  const created = payments.find((p) => p.amount === "42.50");
  expect(created, "payment not found on the server");
  expect(created.date === today(), `date ${created.date}, expected ${today()}`);
  expect(created.method === "cash", `method ${created.method}`);
  await shot("05-payments");
});

let refreshBeforeLogout = null;
await step("logout returns to login and the old refresh token is refused by the server", async () => {
  refreshBeforeLogout = await page.evaluate(() => localStorage.getItem("musicstudio.refresh"));
  expect(refreshBeforeLogout, "no refresh token stored in the web build");
  await page.getByRole("button", { name: "Log out" }).first().click();
  await page.getByLabel("Email").waitFor({ timeout: 10000 });
  const stored = await page.evaluate(() => localStorage.getItem("musicstudio.refresh"));
  expect(stored === null, "refresh token still stored after logout");
  const reuse = await api("/auth/token/refresh/", { method: "POST", body: { refresh: refreshBeforeLogout } });
  expect(reuse.status === 401, `reusing the old refresh token gave ${reuse.status}`);
});

await step("parent sees the read-only portal of the linked child", async () => {
  await login("parent@example.com");
  await page.getByText("Lessons and attendance").waitFor({ timeout: 15000 });
  const buttons = await page.getByRole("button").evaluateAll((els) => els.map((e) => e.getAttribute("aria-label")));
  expect(buttons.every((label) => label === "Log out"), `unexpected actions: ${buttons.join(", ")}`);
  await shot("06-parent-portal");
});

await step("no uncaught errors in the page", async () => {
  expect(consoleErrors.length === 0, consoleErrors.join(" | "));
});

await browser.close();
const failed = results.filter(([r]) => r === "FAIL").length;
console.log(`\n${results.length - failed}/${results.length} steps passed`);
process.exit(failed ? 1 : 0);
