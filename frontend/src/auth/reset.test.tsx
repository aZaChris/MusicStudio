// Forgotten password: request, then choose a new one from the emailed link (US2).
import { fireEvent, screen } from '@testing-library/react'
import { expect, test } from 'vitest'

import { installFakeApi } from '../test/fake-api'
import { renderApp } from '../test/utils'

test('the request answers the same way for any address', async () => {
  const api = installFakeApi({
    'POST /auth/password-reset/': { status: 202, body: { detail: 'check_email' } },
  })
  renderApp('/forgot-password')

  fireEvent.change(await screen.findByLabelText('Email'), { target: { value: 'anyone@example.com' } })
  fireEvent.click(screen.getByRole('button', { name: 'Send the link' }))

  expect(await screen.findByText(/If the address is registered/)).toBeInTheDocument()
  expect(api.callsTo('POST /auth/password-reset/')[0].body).toEqual({ email: 'anyone@example.com' })
})

test('a new password is sent with the link values', async () => {
  const api = installFakeApi({
    'POST /auth/password-reset/confirm/': { status: 200, body: { detail: 'password_changed' } },
  })
  renderApp('/reset-password?uid=MQ&token=tok')

  fireEvent.change(await screen.findByLabelText('New password'), {
    target: { value: 'Contrabbasso-Rosso-88' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Save password' }))

  expect(await screen.findByText('Your password was changed. You can sign in.')).toBeInTheDocument()
  expect(api.callsTo('POST /auth/password-reset/confirm/')[0].body).toEqual({
    uid: 'MQ',
    token: 'tok',
    new_password: 'Contrabbasso-Rosso-88',
  })
})

test('a used or expired link is explained, and the password rules are shown', async () => {
  const api = installFakeApi({
    'POST /auth/password-reset/confirm/': { status: 400, body: { token: 'invalid_or_expired' } },
  })
  renderApp('/reset-password?uid=MQ&token=old')

  fireEvent.change(await screen.findByLabelText('New password'), {
    target: { value: 'Contrabbasso-Rosso-88' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Save password' }))
  expect(
    await screen.findByText('This link is not valid or has expired. Ask for a new one.'),
  ).toBeInTheDocument()

  api.route({
    'POST /auth/password-reset/confirm/': {
      status: 400,
      body: { password: ['This password is too common.'] },
    },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Save password' }))
  expect(await screen.findByText(/This password is too common\./)).toBeInTheDocument()
})
