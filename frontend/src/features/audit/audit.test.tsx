// The owner reads the activity log (US8).
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { expect, test } from 'vitest'

import { dashboard, ownerMe, teacherMe } from '../../test/fixtures'
import { renderApp, signedInAs } from '../../test/utils'

const entry = (id: number, action: string, outcome = 'success') => ({
  id,
  created_at: '2026-11-11T10:00:00Z',
  action,
  outcome,
  actor_email: 'mario@example.com',
  target_type: '',
  target_id: null,
  metadata: {},
})

test('the owner sees translated actions and can filter by action', async () => {
  const api = signedInAs(ownerMe, {
    'GET /audit/': (req) => ({
      status: 200,
      body: {
        count: 1,
        next: null,
        previous: null,
        results: req.path.includes('action=payment.record')
          ? [entry(2, 'payment.record')]
          : [entry(1, 'login.failure', 'failure')],
      },
    }),
  })
  renderApp('/audit')

  expect(await screen.findByRole('cell', { name: 'Failed sign-in' })).toBeInTheDocument()
  expect(screen.getByRole('cell', { name: 'failed' })).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Action'), { target: { value: 'payment.record' } })

  expect(await screen.findByRole('cell', { name: 'Payment recorded' })).toBeInTheDocument()
  await waitFor(() =>
    expect(api.callsTo('GET /audit/').some((c) => c.path.includes('action=payment.record'))).toBe(true),
  )
})

test('a teacher is sent back home from the activity log', async () => {
  signedInAs(teacherMe, { 'GET /dashboard/': { status: 200, body: dashboard() } })
  renderApp('/audit')

  expect(await screen.findByText('Hi, mario.rossi')).toBeInTheDocument()
})
