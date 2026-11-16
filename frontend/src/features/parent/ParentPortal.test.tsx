import { fireEvent, screen, waitFor } from '@testing-library/react'
import { beforeEach, expect, test, vi } from 'vitest'

import { goToExternal } from '../../lib/navigate'
import { page } from '../../test/fake-api'
import { lesson, parentMe, payment, receipt, student } from '../../test/fixtures'
import { renderApp, signedInAs } from '../../test/utils'

vi.mock('../../lib/navigate', () => ({ goToExternal: vi.fn() }))
beforeEach(() => vi.mocked(goToExternal).mockClear())

const routes = {
  'GET /students/': {
    status: 200,
    body: page([student(7, { full_name: 'Giulia Rossi' }), student(8, { full_name: 'Marco Rossi' })]),
  },
  'GET /students/7/lessons/': {
    status: 200,
    body: [lesson({ id: 1, status: 'completed', notes: 'Bravissima' })],
  },
  'GET /students/8/lessons/': { status: 200, body: [lesson({ id: 2, student: 8, status: 'no_show' })] },
  'GET /payments/?student=7': { status: 200, body: page([payment(1)]) },
  'GET /payments/?student=8': {
    status: 200,
    body: page([payment(2, { student: 8, amount: '90.00', status: 'overdue' })]),
  },
}

test('a parent switches between two children; payments are filtered by the server', async () => {
  const api = signedInAs(parentMe, routes)
  renderApp('/')

  expect(await screen.findByText('Bravissima')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('tab', { name: 'Marco Rossi' }))

  expect(await screen.findByText('No-show')).toBeInTheDocument()
  expect(await screen.findByText('Overdue')).toBeInTheDocument()
  expect(api.callsTo('GET /payments/').map((c) => c.path)).toEqual([
    '/payments/?student=7',
    '/payments/?student=8',
  ])
})

test('the portal is read-only: no action changes data', async () => {
  signedInAs(parentMe, routes)
  renderApp('/')
  await screen.findByText('Bravissima')

  const actions = screen.getAllByRole('button').map((b) => b.getAttribute('aria-label') ?? b.textContent)
  expect(actions).toEqual(['Light', 'Dark', 'Italiano', 'English', 'Log out'])
})

const openFor = (studentIds: number[], over = {}) => ({
  account_holder: 'Studio Armonia SRL',
  iban: 'IT60X0542811101000000123456',
  bank_name: 'Banca Esempio',
  note: 'Write the child name',
  links: [{ label: 'PayPal', url: 'https://paypal.me/armonia' }],
  updated_at: '2026-11-15T10:00:00Z',
  studio_id: 100,
  studio_name: 'Studio Armonia',
  student_ids: studentIds,
  notice: 'Payment happens outside MusicStudio and is not verified by it.',
  ...over,
})

test('how to pay appears for the child with an open package and for no other', async () => {
  signedInAs(parentMe, {
    ...routes,
    'GET /payment-instructions/open/': { status: 200, body: [openFor([7])] },
  })
  renderApp('/')

  expect(await screen.findByText(/How to pay — Studio Armonia/)).toBeInTheDocument()
  expect(screen.getByText('IT60X0542811101000000123456')).toBeInTheDocument()
  expect(screen.getByText('Write the child name')).toBeInTheDocument()
  const link = screen.getByRole('link', { name: 'PayPal' })
  expect(link).toHaveAttribute('href', 'https://paypal.me/armonia')
  expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  expect(screen.getByText(/You pay outside MusicStudio/)).toBeInTheDocument()

  fireEvent.click(screen.getByRole('tab', { name: 'Marco Rossi' })) // child 8 owes nothing
  await screen.findByText('No-show')
  expect(screen.queryByText(/How to pay/)).not.toBeInTheDocument()
})

test('with nothing to pay, or no instructions saved, the portal shows nothing about paying', async () => {
  signedInAs(parentMe, { ...routes, 'GET /payment-instructions/open/': { status: 200, body: [] } })
  renderApp('/')

  await screen.findByText('Bravissima')
  expect(screen.queryByText(/How to pay/)).not.toBeInTheDocument()
  expect(screen.queryByText(/IBAN/)).not.toBeInTheDocument()
})

test('two studios: each studio shows only for the child that owes it', async () => {
  signedInAs(parentMe, {
    ...routes,
    'GET /payment-instructions/open/': {
      status: 200,
      body: [
        openFor([7]),
        openFor([8], {
          studio_id: 200,
          studio_name: 'Scuola Due',
          account_holder: 'Scuola Due SRL',
          iban: 'DE89370400440532013000',
        }),
      ],
    },
  })
  renderApp('/')

  expect(await screen.findByText(/How to pay — Studio Armonia/)).toBeInTheDocument()
  expect(screen.queryByText(/Scuola Due/)).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('tab', { name: 'Marco Rossi' }))
  expect(await screen.findByText(/How to pay — Scuola Due/)).toBeInTheDocument()
  expect(screen.getByText('DE89370400440532013000')).toBeInTheDocument()
  expect(screen.queryByText(/Studio Armonia/)).not.toBeInTheDocument()
})

test('a parent lists the issued receipts of the child and downloads one, but cannot issue', async () => {
  const click = vi.fn<() => void>()
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(click)
  vi.stubGlobal('URL', { ...URL, createObjectURL: vi.fn(() => 'blob:x'), revokeObjectURL: vi.fn() })
  const api = signedInAs(parentMe, {
    ...routes,
    'GET /receipts/?student=7': {
      status: 200,
      body: page([receipt(5), receipt(6, { number: '2026-0002', cancelled: true })]),
    },
    'GET /receipts/5/pdf/': { status: 200, body: { any: 'pdf' } },
  })
  renderApp('/')

  expect(await screen.findByText('2026-0001')).toBeInTheDocument()
  expect(screen.getByText(/cancelled/)).toBeInTheDocument()
  fireEvent.click(screen.getAllByRole('button', { name: 'Download' })[0])

  await waitFor(() => expect(click).toHaveBeenCalledTimes(1))
  expect(api.callsTo('GET /receipts/5/pdf/')).toHaveLength(1)
  expect(screen.queryByRole('button', { name: /^Receipt/ })).not.toBeInTheDocument() // no issuing
})

test('a child with no issued receipts shows no receipts section', async () => {
  signedInAs(parentMe, { ...routes, 'GET /receipts/?student=7': { status: 200, body: page([]) } })
  renderApp('/')

  await screen.findByText('Bravissima')
  expect(screen.queryByText('Receipts')).not.toBeInTheDocument()
})

// --- Pay online, straight to the studio's own Stripe account (US2, phase 9) -----------------

const payableStudent = (canPay: boolean) =>
  student(7, {
    full_name: 'Giulia Rossi',
    active_package: { ...student(7).active_package!, price: '150.00', can_pay_online: canPay },
  })
const payRoutes = (canPay: boolean) => ({
  ...routes,
  'GET /students/': { status: 200, body: page([payableStudent(canPay)]) },
})

test('a parent sees how much they pay and is sent to Stripe, not charged by MusicStudio', async () => {
  const api = signedInAs(parentMe, {
    ...payRoutes(true),
    'POST /packages/107/checkout/': {
      status: 200,
      body: {
        checkout_id: 'c1',
        url: 'https://checkout.stripe.com/c/pay/cs_1',
        expires_at: '2026-11-16T12:00:00Z',
      },
    },
  })
  renderApp('/')

  fireEvent.click(await screen.findByRole('button', { name: /Pay .*150.* online/ }))

  await waitFor(() => expect(goToExternal).toHaveBeenCalledWith('https://checkout.stripe.com/c/pay/cs_1'))
  expect(api.callsTo('POST /packages/107/checkout/')).toHaveLength(1)
  expect(screen.getByText(/no real money is charged/)).toBeInTheDocument()
})

test('no pay button when the studio does not take online payments', async () => {
  signedInAs(parentMe, payRoutes(false))
  renderApp('/')
  await screen.findByText('Bravissima')

  expect(screen.queryByRole('button', { name: /online/ })).not.toBeInTheDocument()
})

test('when the server refuses, the message is shown and the payment details stay available', async () => {
  signedInAs(parentMe, {
    ...payRoutes(true),
    'GET /payment-instructions/open/': { status: 200, body: [openFor([7])] },
    'POST /packages/107/checkout/': {
      status: 409,
      body: { detail: 'This studio does not accept online payments.', code: 'online_payments_not_available' },
    },
  })
  renderApp('/')

  fireEvent.click(await screen.findByRole('button', { name: /Pay .*150.* online/ }))

  expect(await screen.findByText(/does not take online payments at the moment/)).toBeInTheDocument()
  expect(screen.getByText(/How to pay — Studio Armonia/)).toBeInTheDocument()
  expect(goToExternal).not.toHaveBeenCalled()
})

test('an unreachable provider shows a message and nobody is redirected', async () => {
  signedInAs(parentMe, {
    ...payRoutes(true),
    'POST /packages/107/checkout/': { status: 503, body: { detail: 'down', code: 'payments_unavailable' } },
  })
  renderApp('/')

  fireEvent.click(await screen.findByRole('button', { name: /Pay .*150.* online/ }))

  expect(await screen.findByRole('alert')).toBeInTheDocument()
  expect(goToExternal).not.toHaveBeenCalled()
})
