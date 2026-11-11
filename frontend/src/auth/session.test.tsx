// Page load, expired sessions and logout against the real app (US1).
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { expect, test } from 'vitest'

import { session } from '../api/client'
import { installFakeApi, offline, page } from '../test/fake-api'
import { dashboard, parentMe, teacherMe } from '../test/fixtures'
import { renderApp, signedInAs } from '../test/utils'

test('without a session the portal opens on the landing page, with a way in', async () => {
  installFakeApi()
  renderApp('/')
  expect(await screen.findByRole('heading', { level: 1 })).toHaveTextContent(
    'The register of your music school',
  )
  expect(screen.getAllByRole('link', { name: 'Create your studio account' })[0]).toHaveAttribute(
    'href',
    '/register',
  )
  expect(screen.getAllByRole('link', { name: 'Log in' })[0]).toHaveAttribute('href', '/login')
})

test('a protected page without a session still goes to the login page', async () => {
  installFakeApi()
  renderApp('/students')
  expect(await screen.findByLabelText('Email')).toBeInTheDocument()
})

test('wrong credentials show a message and store nothing', async () => {
  const api = installFakeApi({ 'POST /auth/token/': { status: 401, body: { detail: 'No active account' } } })
  renderApp('/login')

  fireEvent.change(await screen.findByLabelText('Email'), { target: { value: 'x@example.com' } })
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'wrong' } })
  fireEvent.click(screen.getByRole('button', { name: 'Log in' }))

  expect(await screen.findByText('Invalid email or password.')).toBeInTheDocument()
  expect(api.callsTo('GET /auth/me/')).toHaveLength(0)
  expect(session.refreshToken()).toBeNull()
})

test('a teacher signs in and lands on the dashboard', async () => {
  installFakeApi({
    'POST /auth/token/': { status: 200, body: { access: 'a', refresh: 'r' } },
    'GET /auth/me/': { status: 200, body: teacherMe },
    'GET /dashboard/': { status: 200, body: dashboard() },
  })
  renderApp('/login')

  fireEvent.change(await screen.findByLabelText('Email'), { target: { value: teacherMe.email } })
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'password123' } })
  fireEvent.click(screen.getByRole('button', { name: 'Log in' }))

  expect(await screen.findByText('Hi, mario.rossi')).toBeInTheDocument()
})

test('page load re-verifies the stored session and routes by the server role', async () => {
  const api = signedInAs(parentMe, { 'GET /students/': { status: 200, body: page([]) } })
  renderApp('/')

  expect(await screen.findByText('No students are linked to your account yet.')).toBeInTheDocument()
  expect(api.callsTo('GET /auth/me/')).toHaveLength(1)
})

test('a stored session that cannot be confirmed (offline) is kept, with a retry', async () => {
  session.start({ access: 'a', refresh: 'refresh-1' })
  offline()
  renderApp('/students')

  expect(await screen.findByText('Cannot reach the server to check your account.')).toBeInTheDocument()
  expect(session.refreshToken()).toBe('refresh-1')
})

test('when the session cannot be renewed the user is sent to login with an explanation', async () => {
  signedInAs(teacherMe, {
    'GET /dashboard/': { status: 401 },
    'POST /auth/token/refresh/': { status: 401, body: { detail: 'Token is blacklisted' } },
  })
  renderApp('/')

  expect(await screen.findByText('Your session has ended. Please log in again.')).toBeInTheDocument()
  expect(session.refreshToken()).toBeNull()
})

test('logout ends the session on the server, then locally', async () => {
  const api = signedInAs(teacherMe, {
    'GET /dashboard/': { status: 200, body: dashboard() },
    'POST /auth/logout/': { status: 205 },
  })
  renderApp('/')

  fireEvent.click(await screen.findByRole('button', { name: 'Log out' }))

  expect(await screen.findByLabelText('Email')).toBeInTheDocument()
  expect(api.callsTo('POST /auth/logout/')[0].body).toEqual({ refresh: 'refresh-1' })
  expect(session.refreshToken()).toBeNull()
})

test('logout right after a rotation sends the newest refresh token', async () => {
  const api = signedInAs(teacherMe, {
    'GET /dashboard/': { status: 200, body: dashboard() },
    'POST /auth/token/refresh/': { status: 200, body: { access: 'access-2', refresh: 'refresh-2' } },
    'POST /auth/logout/': (req) => {
      if (req.authorization !== 'Bearer access-2') return { status: 401 }
      return (req.body as { refresh: string }).refresh === 'refresh-2'
        ? { status: 205 }
        : { status: 400, body: { refresh: ['Token is blacklisted'] } }
    },
  })
  renderApp('/')
  await screen.findByRole('button', { name: 'Log out' })
  session.start({ access: 'expired', refresh: 'refresh-1' }) // the access token expires meanwhile

  fireEvent.click(screen.getByRole('button', { name: 'Log out' }))

  await waitFor(() =>
    expect(api.callsTo('POST /auth/logout/').map((c) => (c.body as { refresh: string }).refresh)).toContain(
      'refresh-2',
    ),
  )
  expect(await screen.findByLabelText('Email')).toBeInTheDocument()
})

test('logout still signs out locally when the server is unreachable', async () => {
  signedInAs(teacherMe, { 'GET /dashboard/': { status: 200, body: dashboard() } })
  renderApp('/')
  await screen.findByRole('button', { name: 'Log out' })
  offline()

  fireEvent.click(screen.getByRole('button', { name: 'Log out' }))

  expect(await screen.findByLabelText('Email')).toBeInTheDocument()
  expect(session.refreshToken()).toBeNull()
})

test("after logout and a new sign-in, nothing of the previous user's data is shown", async () => {
  const api = signedInAs(teacherMe, {
    'GET /dashboard/': { status: 200, body: dashboard({ active_students_count: 12 }) },
    'POST /auth/logout/': { status: 205 },
  })
  renderApp('/')
  expect(await screen.findByText('12')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Log out' }))
  await screen.findByLabelText('Email')

  let release: () => void = () => undefined
  api.route({
    'POST /auth/token/': { status: 200, body: { access: 'b', refresh: 'r2' } },
    'GET /auth/me/': { status: 200, body: { ...teacherMe, id: 9, email: 'luca@example.com' } },
    'GET /dashboard/': () =>
      new Promise((resolve) => {
        release = () => resolve({ status: 200, body: dashboard({ active_students_count: 4 }) })
      }),
  })
  fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'luca@example.com' } })
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'pw' } })
  fireEvent.click(screen.getByRole('button', { name: 'Log in' }))

  expect(await screen.findByText('Hi, luca')).toBeInTheDocument()
  expect(screen.queryByText('12')).toBeNull() // while the new dashboard is still loading
  release()
  expect(await screen.findByText('4')).toBeInTheDocument()
})
