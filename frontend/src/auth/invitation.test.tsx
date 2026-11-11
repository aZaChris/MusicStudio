// Accepting an invitation from the emailed link (US3).
import { fireEvent, screen } from '@testing-library/react'
import { expect, test } from 'vitest'

import { session } from '../api/client'
import { installFakeApi } from '../test/fake-api'
import { teacherMe } from '../test/fixtures'
import { renderApp } from '../test/utils'

const lookup = {
  role: 'parent',
  studio_name: 'Scuola Zanotti',
  email: 'anna@example.com',
  student_first_names: ['Giulia'],
  existing_account: false,
}

test('a parent sees who invites, must tick consent, and ends up signed in', async () => {
  const api = installFakeApi({
    'GET /invitations/lookup/': { status: 200, body: lookup },
    'POST /invitations/accept/': { status: 201, body: { access: 'a', refresh: 'r' } },
    'GET /auth/me/': {
      status: 200,
      body: { ...teacherMe, role: 'parent', teacher: null, parent_account: { id: 1 } },
    },
    'GET /students/': { status: 200, body: { count: 0, next: null, previous: null, results: [] } },
  })
  renderApp('/invitations/accept?token=secret-token')

  expect(await screen.findByText('Scuola Zanotti invites you as a parent.')).toBeInTheDocument()
  expect(screen.getByText('For: Giulia')).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('First name'), { target: { value: 'Anna' } })
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'Pianoforte-Verde-31' } })
  fireEvent.click(screen.getByLabelText('I accept the terms and the privacy notice'))
  fireEvent.click(screen.getByLabelText(/I consent to the processing of my child's data/))
  fireEvent.click(screen.getByRole('button', { name: 'Accept invitation' }))

  await screen.findByText('No students are linked to your account yet.')
  expect(api.callsTo('GET /invitations/lookup/')[0].path).toContain('token=secret-token')
  expect(api.callsTo('POST /invitations/accept/')[0].body).toMatchObject({
    token: 'secret-token',
    first_name: 'Anna',
    accept_terms: true,
    consent: true,
  })
  expect(session.refreshToken()).toBe('r')
})

test('an invalid, expired or used invitation says so', async () => {
  installFakeApi({ 'GET /invitations/lookup/': { status: 404, body: { detail: 'Not found.' } } })
  renderApp('/invitations/accept?token=old')

  expect(await screen.findByText(/not valid, has expired or was already used/)).toBeInTheDocument()
})

test('an address that already has an account is asked to sign in first', async () => {
  installFakeApi({
    'GET /invitations/lookup/': { status: 200, body: { ...lookup, existing_account: true } },
  })
  renderApp('/invitations/accept?token=t')

  expect(await screen.findByText(/already has an account/)).toBeInTheDocument()
  expect(screen.queryByLabelText('Password')).not.toBeInTheDocument()
})
