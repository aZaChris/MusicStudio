#!/usr/bin/env node
// End-to-end check of the production build against a real local Django backend (T020).
//
// Prerequisites:
//   backend: dev settings (in-memory cache without Redis), `seed_demo`, :8000,
//            CORS_ALLOWED_ORIGINS=http://localhost:4173
//   portal:  VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1 npx vite build
//            npx vite preview --port 4173
// Usage: node scripts/verify-django.mjs [screenshot-dir]
import { chromium } from 'playwright'

const APP = process.env.APP_URL ?? 'http://localhost:4173'
const API = process.env.API_URL ?? 'http://127.0.0.1:8000/api/v1'
const SHOTS = process.argv[2]
const PASSWORD = 'password123'

const results = []
async function step(name, fn) {
  try {
    await fn()
    results.push(true)
    console.log(`PASS  ${name}`)
  } catch (error) {
    results.push(false)
    console.log(`FAIL  ${name}\n      ${String(error.message ?? error).split('\n')[0]}`)
  }
}
const expect = (ok, message) => {
  if (!ok) throw new Error(message)
}

async function api(path, { token, method = 'GET', body } = {}) {
  const res = await fetch(API + path, {
    method,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  })
  return { status: res.status, body: await res.json().catch(() => null) }
}
const tokenFor = async (email) =>
  (await api('/auth/token/', { method: 'POST', body: { email, password: PASSWORD } })).body.access
const pad = (n) => String(n).padStart(2, '0')
const today = () => {
  const d = new Date()
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1280, height: 900 }, locale: 'en-GB' })
const pageErrors = []
page.on('pageerror', (err) => pageErrors.push(err.message))
const shot = async (name) => SHOTS && page.screenshot({ path: `${SHOTS}/${name}.png` })

async function login(email) {
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(PASSWORD)
  await page.getByRole('button', { name: 'Log in' }).click()
}

const ownerToken = await tokenFor('owner@example.com')
const before = (await api('/dashboard/', { token: ownerToken })).body

await step('opens on the login page without a session', async () => {
  await page.goto(APP)
  await page.getByLabel('Email').waitFor({ timeout: 20000 })
})

await step("wrong password shows 'Invalid email or password.'", async () => {
  await page.getByLabel('Email').fill('owner@example.com')
  await page.getByLabel('Password').fill('wrong')
  await page.getByRole('button', { name: 'Log in' }).click()
  await page.getByText('Invalid email or password.').waitFor({ timeout: 10000 })
})

await step("owner signs in and sees the server's dashboard counts", async () => {
  await login('owner@example.com')
  await page.getByText('Hi, owner 👋').waitFor({ timeout: 15000 })
  await page.getByText(String(before.active_students_count), { exact: true }).first().waitFor()
  await shot('01-dashboard')
})

const lesson = before.week.find((l) => l.status === 'scheduled')
await step('completing a lesson with a note is saved on the server', async () => {
  expect(lesson, 'seed has no scheduled lesson this week for the owner')
  await page
    .getByRole('button', { name: new RegExp(lesson.student_name) })
    .first()
    .click()
  await page.getByLabel('Progress note').fill('E2E web: arpeggios')
  await page.getByRole('button', { name: 'Mark complete' }).click()
  await page.getByRole('dialog').waitFor({ state: 'detached', timeout: 30000 })
  const lessons = (await api(`/students/${lesson.student}/lessons/`, { token: ownerToken })).body
  const done = lessons.find((l) => l.id === lesson.id)
  expect(done.status === 'completed' && done.notes === 'E2E web: arpeggios', `lesson is ${done.status}`)
})

await step('reloading a deep route keeps the portal (route fallback) and shows the student', async () => {
  await page.goto(`${APP}/students/${lesson.student}`)
  await page.getByText('E2E web: arpeggios').waitFor({ timeout: 15000 })
  await shot('02-student')
})

await step("a cash payment is registered with today's local date", async () => {
  await page.getByRole('link', { name: /Payments/ }).click()
  const student = (await api('/students/?is_active=true', { token: ownerToken })).body.results[0]
  await page.getByRole('option', { name: student.full_name }).waitFor({ state: 'attached' })
  await page.getByLabel('Student').selectOption(String(student.id))
  await page.getByLabel('Amount').fill('42.50')
  await page.getByLabel('Method').selectOption('cash')
  await page.getByRole('button', { name: 'Register payment' }).click()
  await page.getByText('Payment registered.').waitFor({ timeout: 10000 })
  const payments = (await api(`/payments/?student=${student.id}`, { token: ownerToken })).body.results
  const created = payments.find((p) => p.amount === '42.50')
  expect(created && created.date === today(), `payment date ${created?.date}, expected ${today()}`)
  await shot('03-payments')
})

await step('the access token is not in localStorage; the refresh token is', async () => {
  const stored = await page.evaluate(() => ({ ...localStorage }))
  expect(stored['musicstudio.refresh'], 'no refresh token stored')
  expect(!Object.keys(stored).some((k) => /access/i.test(k)), `access token stored: ${Object.keys(stored)}`)
})

await step('logout returns to login and the old refresh token is refused by the server', async () => {
  const refresh = await page.evaluate(() => localStorage.getItem('musicstudio.refresh'))
  await page.getByRole('button', { name: 'Log out' }).click()
  await page.getByLabel('Email').waitFor({ timeout: 10000 })
  const reuse = await api('/auth/token/refresh/', { method: 'POST', body: { refresh } })
  expect(reuse.status === 401, `reusing the old refresh token gave ${reuse.status}`)
})

await step('parent sees the read-only portal', async () => {
  await login('parent@example.com')
  await page.getByText('Lessons and attendance').waitFor({ timeout: 15000 })
  await shot('04-parent')
})

await step('no uncaught errors in the page', async () => {
  expect(pageErrors.length === 0, pageErrors.join(' | '))
})

await browser.close()
const passed = results.filter(Boolean).length
console.log(`\n${passed}/${results.length} steps passed`)
process.exit(passed === results.length ? 0 : 1)
