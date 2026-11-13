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
