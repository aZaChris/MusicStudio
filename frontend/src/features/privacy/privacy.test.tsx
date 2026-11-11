// Consents, export and erasure for families (US6, US7).
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { expect, test, vi } from 'vitest'

import { session } from '../../api/client'
import { page } from '../../test/fake-api'
import { parentMe, studentMe } from '../../test/fixtures'
import { renderApp, signedInAs } from '../../test/utils'

const consent = {
  id: 5,
  notice_version: '2026-11-draft',
  given_at: '2026-11-01T10:00:00Z',
  withdrawn_at: null,
  children: [{ id: 7, name: 'Giulia Rossi' }],
}

test('consents are listed and withdrawing needs the password', async () => {
  const api = signedInAs(parentMe, {
    'GET /privacy/consents/': { status: 200, body: [consent] },
    'POST /privacy/consents/5/withdraw/': { status: 202, body: { detail: 'withdrawn' } },
  })
  renderApp('/privacy')

  expect(await screen.findByText('Giulia Rossi')).toBeInTheDocument()
  const withdraw = screen.getByRole('button', { name: 'Withdraw consent' })
  expect(withdraw).toBeDisabled()
  fireEvent.change(screen.getByLabelText(/Your password/), { target: { value: 'password123' } })
  fireEvent.click(withdraw)

  await waitFor(() => expect(api.callsTo('POST /privacy/consents/5/withdraw/')).toHaveLength(1))
  expect(api.callsTo('POST /privacy/consents/5/withdraw/')[0].body).toEqual({ password: 'password123' })
})

test('the export is downloaded as a file', async () => {
  const create = vi.fn(() => 'blob:x')
  vi.stubGlobal('URL', { createObjectURL: create, revokeObjectURL: vi.fn() })
  const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined)
  const api = signedInAs(parentMe, {
    'GET /privacy/consents/': { status: 200, body: [] },
    'GET /privacy/export/': { status: 200, body: { account: { email: parentMe.email }, children: [] } },
  })
  renderApp('/privacy')

  fireEvent.click(await screen.findByRole('button', { name: 'Download my data' }))

  await waitFor(() => expect(click).toHaveBeenCalled())
  expect(api.callsTo('GET /privacy/export/')).toHaveLength(1)
  expect(create).toHaveBeenCalled()
  click.mockRestore()
  vi.unstubAllGlobals()
})

test('closing the account needs the password and a confirmation, then signs out', async () => {
  const api = signedInAs(parentMe, {
    'GET /privacy/consents/': { status: 200, body: [] },
    'POST /privacy/erase/': { status: 202, body: { detail: 'erased' } },
    'POST /auth/logout/': { status: 205 },
  })
  renderApp('/privacy')

  const erase = await screen.findByRole('button', { name: 'Close my account' })
  expect(erase).toBeDisabled()
  fireEvent.change(screen.getByLabelText(/Your password/), { target: { value: 'password123' } })
  expect(erase).toBeDisabled() // still needs the confirmation
  fireEvent.click(screen.getByLabelText('I understand this cannot be undone'))
  fireEvent.click(erase)

  expect(await screen.findByLabelText('Email')).toBeInTheDocument()
  expect(api.callsTo('POST /privacy/erase/')[0].body).toEqual({ password: 'password123' })
  expect(session.refreshToken()).toBeNull()
})

test('an open checkout blocks the erasure with the server message', async () => {
  signedInAs(parentMe, {
    'GET /privacy/consents/': { status: 200, body: [] },
    'POST /privacy/erase/': { status: 409, body: { detail: 'An online payment is still pending.' } },
  })
  renderApp('/privacy')

  fireEvent.change(await screen.findByLabelText(/Your password/), { target: { value: 'password123' } })
  fireEvent.click(screen.getByLabelText('I understand this cannot be undone'))
  fireEvent.click(screen.getByRole('button', { name: 'Close my account' }))

  expect(await screen.findByText(/online payment is still pending/)).toBeInTheDocument()
  expect(session.refreshToken()).toBe('refresh-1')
})

test('an adult student sees the family portal and can reach the privacy page', async () => {
  signedInAs(studentMe, {
    'GET /students/': { status: 200, body: page([]) },
    'GET /privacy/consents/': { status: 200, body: [] },
  })
  renderApp('/')

  expect(await screen.findByText('No students are linked to your account yet.')).toBeInTheDocument()
  expect(screen.getByText('Student')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('link', { name: 'Privacy' }))
  expect(await screen.findByRole('heading', { name: 'Privacy and account' })).toBeInTheDocument()
})
