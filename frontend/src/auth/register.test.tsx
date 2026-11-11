// Sign-up, email confirmation and the "unconfirmed" path of the login page (US1).
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { expect, test } from 'vitest'

import { installFakeApi } from '../test/fake-api'
import { renderApp } from '../test/utils'

const fill = (label: string, value: string) =>
  fireEvent.change(screen.getByLabelText(label), { target: { value } })

test('a studio owner signs up and is told to check the email', async () => {
  const api = installFakeApi({ 'POST /auth/register/': { status: 202, body: { detail: 'check_email' } } })
  renderApp('/register')

  fill('First name', 'Marta')
  fill('Last name', 'Zanotti')
  fill('Studio name', 'Scuola Zanotti')
  fill('Email', 'marta@example.com')
  fill('Password', 'Violoncello-Azzurro-77')
  fireEvent.click(screen.getByLabelText('I accept the terms and the privacy notice'))
  fireEvent.click(screen.getByRole('button', { name: 'Create account' }))

  expect(await screen.findByText(/we sent a link to confirm it/)).toBeInTheDocument()
  expect(api.callsTo('POST /auth/register/')[0].body).toMatchObject({
    email: 'marta@example.com',
    studio_name: 'Scuola Zanotti',
    accept_terms: true,
    preferred_language: 'en',
  })
})

test('registration errors from the server are shown', async () => {
  installFakeApi({
    'POST /auth/register/': { status: 400, body: { password: ['This password is too common.'] } },
  })
  renderApp('/register')

  fill('First name', 'M')
  fill('Last name', 'Z')
  fill('Studio name', 'S')
  fill('Email', 'm@example.com')
  fill('Password', 'password')
  fireEvent.click(screen.getByLabelText('I accept the terms and the privacy notice'))
  fireEvent.click(screen.getByRole('button', { name: 'Create account' }))

  expect(await screen.findByRole('alert')).toHaveTextContent('This password is too common.')
})

test('the confirmation link is sent to the backend once, and success is shown', async () => {
  const api = installFakeApi({ 'POST /auth/confirm-email/': { status: 200, body: { detail: 'ok' } } })
  renderApp('/confirm-email?uid=MQ&token=abc')

  expect(await screen.findByText('Your email is confirmed. You can sign in.')).toBeInTheDocument()
  expect(api.callsTo('POST /auth/confirm-email/')).toHaveLength(1)
  expect(api.callsTo('POST /auth/confirm-email/')[0].body).toEqual({ uid: 'MQ', token: 'abc' })
})

test('an expired confirmation link says so', async () => {
  installFakeApi({ 'POST /auth/confirm-email/': { status: 400, body: { token: ['invalid_or_expired'] } } })
  renderApp('/confirm-email?uid=MQ&token=old')

  expect(await screen.findByText(/not valid or has expired/)).toBeInTheDocument()
})

test('login of an unconfirmed account offers to send the link again', async () => {
  const api = installFakeApi({
    'POST /auth/token/': {
      status: 401,
      body: { detail: 'Confirm your email address before signing in.', code: 'email_not_confirmed' },
    },
    'POST /auth/confirm-email/resend/': { status: 202, body: { detail: 'check_email' } },
  })
  renderApp('/login')

  fireEvent.change(await screen.findByLabelText('Email'), { target: { value: 'new@example.com' } })
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'password123' } })
  fireEvent.click(screen.getByRole('button', { name: 'Log in' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Send the link again' }))

  expect(await screen.findByText('We sent you a new confirmation link.')).toBeInTheDocument()
  expect(api.callsTo('POST /auth/confirm-email/resend/')[0].body).toEqual({ email: 'new@example.com' })
})

test('login with the second factor sends the code and signs in', async () => {
  const api = installFakeApi({
    'POST /auth/token/': { status: 200, body: { mfa_required: true, mfa_token: 'signed-mfa' } },
    'POST /auth/mfa/verify/': { status: 200, body: { access: 'a', refresh: 'r' } },
    'GET /auth/me/': {
      status: 200,
      body: {
        id: 1,
        email: 't@example.com',
        role: 'teacher',
        preferred_language: 'en',
        email_verified: true,
        mfa_enabled: true,
        teacher: { id: 10, studio: 100, is_owner: false },
        parent_account: null,
      },
    },
    'GET /dashboard/': { status: 200, body: {} },
    'GET /payments/': { status: 200, body: { count: 0, next: null, previous: null, results: [] } },
  })
  renderApp('/login')

  fireEvent.change(await screen.findByLabelText('Email'), { target: { value: 't@example.com' } })
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'password123' } })
  fireEvent.click(screen.getByRole('button', { name: 'Log in' }))
  fireEvent.change(await screen.findByLabelText(/Verification code/), { target: { value: '123456' } })
  fireEvent.click(screen.getByRole('button', { name: 'Log in' }))

  await waitFor(() => expect(api.callsTo('POST /auth/mfa/verify/')).toHaveLength(1))
  expect(api.callsTo('POST /auth/mfa/verify/')[0].body).toEqual({ mfa_token: 'signed-mfa', code: '123456' })
})
