// The studio's own Stripe account: owner starts and refreshes it, teachers only read (US1, phase 9).
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { beforeEach, expect, test, vi } from 'vitest'

import { goToExternal } from '../../lib/navigate'
import { ownerMe, teacherMe } from '../../test/fixtures'
import { renderApp, signedInAs } from '../../test/utils'

vi.mock('../../lib/navigate', () => ({ goToExternal: vi.fn() }))

const instructions = {
  account_holder: '',
  iban: '',
  bank_name: '',
  note: '',
  links: [],
  updated_at: null,
}
const account = (state: string, extra = {}) => ({
  state,
  can_accept_online: state === 'active',
  test_mode: true,
  dashboard_url: state === 'not_started' ? null : 'https://dashboard.stripe.com/test/dashboard',
  state_changed_at: '2026-11-16T10:00:00Z',
  needs_attention: [],
  ...extra,
})
const routes = (body: object) => ({
  'GET /payment-instructions/': { status: 200, body: instructions },
  'GET /payment-account/': { status: 200, body },
})

beforeEach(() => vi.mocked(goToExternal).mockClear())

test('with the feature off the section is not there at all', async () => {
  signedInAs(ownerMe, { 'GET /payment-instructions/': { status: 200, body: instructions } })
  renderApp('/payment-instructions')

  expect(await screen.findByLabelText('IBAN')).toBeInTheDocument()
  expect(screen.queryByText('Online payments')).not.toBeInTheDocument()
})

test('the owner starts onboarding and is sent to the Stripe page', async () => {
  const api = signedInAs(ownerMe, {
    ...routes(account('not_started')),
    'POST /payment-account/onboarding/': {
      status: 200,
      body: { url: 'https://connect.stripe.com/setup/s/acct_1/x', expires_at: null },
    },
  })
  renderApp('/payment-instructions')

  expect(await screen.findByTestId('account-state')).toHaveTextContent('Not started')
  expect(screen.getByRole('note', { name: '' })).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Open my account on Stripe' }))

  await waitFor(() =>
    expect(goToExternal).toHaveBeenCalledWith('https://connect.stripe.com/setup/s/acct_1/x'),
  )
  expect(api.callsTo('POST /payment-account/onboarding/')).toHaveLength(1)
})

test('the test-mode warning is always shown while in test mode', async () => {
  signedInAs(ownerMe, routes(account('active')))
  renderApp('/payment-instructions')

  expect(await screen.findByText(/no real money moves yet/)).toBeInTheDocument()
  expect(screen.getByTestId('account-state')).toHaveTextContent('Active')
  expect(screen.getByRole('link', { name: 'Open my Stripe page' })).toHaveAttribute(
    'href',
    'https://dashboard.stripe.com/test/dashboard',
  )
})

test('a teacher reads the state but gets no button to change it', async () => {
  signedInAs(teacherMe, routes(account('information_needed')))
  renderApp('/payment-instructions')

  expect(await screen.findByTestId('account-state')).toHaveTextContent('Information needed')
  expect(screen.getByText('Only the studio owner can open or change the account.')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /Stripe/ })).not.toBeInTheDocument()
})

test('coming back from Stripe reads the account again and shows the new state', async () => {
  const api = signedInAs(ownerMe, {
    ...routes(account('information_needed')),
    'POST /payment-account/refresh/': { status: 200, body: account('active') },
  })
  renderApp('/payment-instructions?return=1')

  await waitFor(() => expect(screen.getByTestId('account-state')).toHaveTextContent('Active'))
  expect(api.callsTo('POST /payment-account/refresh/')).toHaveLength(1)
})

test('the "check status" button reads the account again', async () => {
  const api = signedInAs(ownerMe, {
    ...routes(account('active')),
    'POST /payment-account/refresh/': { status: 200, body: account('restricted') },
  })
  renderApp('/payment-instructions')

  fireEvent.click(await screen.findByRole('button', { name: 'Check status' }))

  await waitFor(() => expect(screen.getByTestId('account-state')).toHaveTextContent('Restricted'))
  expect(api.callsTo('POST /payment-account/refresh/')).toHaveLength(1)
})

test('an unreachable Stripe shows a message and sends nobody anywhere', async () => {
  signedInAs(ownerMe, {
    ...routes(account('not_started')),
    'POST /payment-account/onboarding/': {
      status: 503,
      body: { detail: 'The payment provider is not reachable.', code: 'payments_unavailable' },
    },
  })
  renderApp('/payment-instructions')

  fireEvent.click(await screen.findByRole('button', { name: 'Open my account on Stripe' }))

  expect(await screen.findByRole('alert')).toBeInTheDocument()
  expect(goToExternal).not.toHaveBeenCalled()
})

test('a disconnected account offers to start again and then goes to Stripe', async () => {
  const api = signedInAs(ownerMe, {
    ...routes(account('disconnected')),
    'POST /payment-account/restart/': { status: 204 },
    'POST /payment-account/onboarding/': {
      status: 200,
      body: { url: 'https://connect.stripe.com/setup/s/acct_2/y', expires_at: null },
    },
  })
  renderApp('/payment-instructions')

  fireEvent.click(await screen.findByRole('button', { name: 'Start again' }))

  await waitFor(() =>
    expect(goToExternal).toHaveBeenCalledWith('https://connect.stripe.com/setup/s/acct_2/y'),
  )
  expect(api.callsTo('POST /payment-account/restart/')).toHaveLength(1)
})

test('events that do not match the register are listed without any personal data', async () => {
  signedInAs(
    ownerMe,
    routes(
      account('active', {
        needs_attention: [
          { id: 1, kind: 'refund_unmatched', received_at: '2026-11-16T10:00:00Z', amount: '40.00' },
        ],
      }),
    ),
  )
  renderApp('/payment-instructions')

  expect(await screen.findByText(/A refund that matches no payment in the register/)).toBeInTheDocument()
  expect(screen.getByText(/40.00 €/)).toBeInTheDocument()
})
