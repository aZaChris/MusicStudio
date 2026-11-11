// Password change and two-step verification setup (US2, US5).
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { expect, test } from 'vitest'

import { session } from '../../api/client'
import { dashboard, teacherMe } from '../../test/fixtures'
import { page } from '../../test/fake-api'
import { renderApp, signedInAs } from '../../test/utils'

const base = {
  'GET /dashboard/': { status: 200, body: dashboard() },
  'GET /auth/mfa/': { status: 200, body: { enabled: false, recovery_codes_left: 0 } },
}

test('changing the password signs the user out', async () => {
  const api = signedInAs(teacherMe, {
    ...base,
    'POST /auth/password/change/': { status: 200, body: { detail: 'password_changed' } },
    'POST /auth/logout/': { status: 205 },
  })
  renderApp('/account')

  fireEvent.change(await screen.findByLabelText('Current password'), { target: { value: 'old-pass-1' } })
  fireEvent.change(screen.getByLabelText('New password'), { target: { value: 'Contrabbasso-Rosso-88' } })
  fireEvent.click(screen.getByRole('button', { name: 'Change password' }))

  expect(await screen.findByLabelText('Email')).toBeInTheDocument() // back on the login page
  expect(api.callsTo('POST /auth/password/change/')[0].body).toEqual({
    current_password: 'old-pass-1',
    new_password: 'Contrabbasso-Rosso-88',
  })
  expect(session.refreshToken()).toBeNull()
})

test('a wrong current password shows the server message and stays signed in', async () => {
  signedInAs(teacherMe, {
    ...base,
    'POST /auth/password/change/': { status: 400, body: { current_password: ['Wrong password.'] } },
  })
  renderApp('/account')

  fireEvent.change(await screen.findByLabelText('Current password'), { target: { value: 'nope' } })
  fireEvent.change(screen.getByLabelText('New password'), { target: { value: 'Contrabbasso-Rosso-88' } })
  fireEvent.click(screen.getByRole('button', { name: 'Change password' }))

  expect(await screen.findByText(/Wrong password\./)).toBeInTheDocument()
  expect(session.refreshToken()).toBe('refresh-1')
})

test('setting up two-step verification shows the secret, then the recovery codes once', async () => {
  const api = signedInAs(teacherMe, {
    ...base,
    'POST /auth/mfa/setup/': {
      status: 201,
      body: {
        secret: 'JBSWY3DPEHPK3PXP',
        otpauth_uri: 'otpauth://totp/MusicStudio:t?secret=JBSWY3DPEHPK3PXP',
      },
    },
    'POST /auth/mfa/confirm/': { status: 200, body: { recovery_codes: ['aaaaaa-bbbb', 'cccccc-dddd'] } },
  })
  renderApp('/account')

  fireEvent.click(await screen.findByRole('button', { name: 'Turn on' }))
  expect(await screen.findByLabelText('Secret')).toHaveTextContent('JBSWY3DPEHPK3PXP')
  fireEvent.change(screen.getByLabelText('Verification code'), { target: { value: '123456' } })
  fireEvent.click(screen.getByRole('button', { name: 'Confirm' }))

  expect(await screen.findByText('aaaaaa-bbbb')).toBeInTheDocument()
  expect(api.callsTo('POST /auth/mfa/confirm/')[0].body).toEqual({ code: '123456' })
  fireEvent.click(screen.getByRole('button', { name: 'I saved them' }))
  await waitFor(() => expect(screen.queryByText('aaaaaa-bbbb')).not.toBeInTheDocument())
})

test('with two-step on, turning it off needs password and code', async () => {
  const api = signedInAs(teacherMe, {
    ...base,
    'GET /auth/mfa/': { status: 200, body: { enabled: true, recovery_codes_left: 9 } },
    'POST /auth/mfa/disable/': { status: 204 },
  })
  renderApp('/account')

  expect(await screen.findByText('On. 9 recovery codes left.')).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'password123' } })
  fireEvent.change(screen.getByLabelText('Verification code'), { target: { value: '654321' } })
  fireEvent.click(screen.getByRole('button', { name: 'Turn off' }))

  await waitFor(() => expect(api.callsTo('POST /auth/mfa/disable/')).toHaveLength(1))
  expect(api.callsTo('POST /auth/mfa/disable/')[0].body).toEqual({ password: 'password123', code: '654321' })
  void page
})
