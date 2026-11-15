import { fireEvent, screen } from '@testing-library/react'
import { expect, test } from 'vitest'

import { page } from '../../test/fake-api'
import { lesson, parentMe, payment, student } from '../../test/fixtures'
import { renderApp, signedInAs } from '../../test/utils'

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
