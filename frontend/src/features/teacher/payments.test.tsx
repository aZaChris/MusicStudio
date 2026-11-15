import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, test } from 'vitest'

import { page } from '../../test/fake-api'
import { payment, student, teacherMe } from '../../test/fixtures'
import { renderApp, signedInAs } from '../../test/utils'

const base = (list: ReturnType<typeof payment>[]) => ({
  'GET /payments/': { status: 200, body: page(list) },
  'GET /students/': { status: 200, body: page([student(7, { full_name: 'Giulia Rossi' })]) },
})

describe('payments register: reversal', () => {
  test('a paid entry offers Reverse; a reversed one and its reversal are history', async () => {
    signedInAs(
      teacherMe,
      base([
        payment(1, { reversed: true, reversal_id: 2, student_name: 'Mario Bianchi' }),
        payment(2, {
          status: 'reversal',
          reversal_of: 1,
          reason: 'wrong student',
          student_name: 'Mario Bianchi',
        }),
        payment(3, { student_name: 'Giulia Rossi' }),
        payment(4, { status: 'pending', student_name: 'Anna Neri' }),
      ]),
    )
    renderApp('/payments')

    await screen.findByText('Anna Neri') // appears only in the table, not in the student select
    const rowsOf = (name: string) =>
      screen.getAllByRole('row').filter((row) => row.textContent?.includes(name))

    // Only the plain paid entry can be reversed.
    expect(within(rowsOf('Giulia Rossi')[0]).getByRole('button', { name: 'Reverse' })).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Reverse' })).toHaveLength(1)
    // The original reads Reversed, the reversal row says what it reverses and why.
    expect(within(rowsOf('Mario Bianchi')[0]).getByText('Reversed')).toBeInTheDocument()
    const reversalRow = rowsOf('Mario Bianchi')[1]
    expect(within(reversalRow).getByText('Reversal')).toBeInTheDocument()
    expect(within(reversalRow).getByText(/Reversal of payment #1/)).toBeInTheDocument()
    expect(within(reversalRow).getByText(/Reason: wrong student/)).toBeInTheDocument()
    // A reversal is not money to collect: only the pending entry counts.
    expect(screen.getByText('1 to collect')).toBeInTheDocument()
  })

  test('reversing asks for a reason and sends it', async () => {
    const api = signedInAs(teacherMe, {
      ...base([payment(3, { student_name: 'Giulia Rossi' })]),
      'POST /payments/3/reverse/': { status: 201, body: payment(9, { status: 'reversal' }) },
    })
    renderApp('/payments')

    fireEvent.click(await screen.findByRole('button', { name: 'Reverse' }))
    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByRole('button', { name: 'Reverse payment' })).toBeDisabled()
    fireEvent.change(within(dialog).getByLabelText(/Reason/), { target: { value: ' wrong student ' } })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Reverse payment' }))

    await waitFor(() => expect(api.callsTo('POST /payments/3/reverse/')).toHaveLength(1))
    expect(api.callsTo('POST /payments/3/reverse/')[0].body).toEqual({ reason: 'wrong student' })
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })

  test('a 409 from the server is shown as its translated sentence', async () => {
    signedInAs(teacherMe, {
      ...base([payment(3)]),
      'POST /payments/3/reverse/': {
        status: 409,
        body: { detail: 'This entry was already reversed.', code: 'already_reversed' },
      },
    })
    renderApp('/payments')

    fireEvent.click(await screen.findByRole('button', { name: 'Reverse' }))
    const dialog = await screen.findByRole('dialog')
    fireEvent.change(within(dialog).getByLabelText(/Reason/), { target: { value: 'x' } })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Reverse payment' }))

    expect(await within(dialog).findByRole('alert')).toHaveTextContent('This entry was already reversed.')
  })

  test('a card entry says that no money is returned', async () => {
    signedInAs(teacherMe, base([payment(3, { method: 'card' })]))
    renderApp('/payments')

    fireEvent.click(await screen.findByRole('button', { name: 'Reverse' }))

    expect(await screen.findByText(/No money is returned/)).toBeInTheDocument()
  })

  test('a bank transfer entry does not show the card notice', async () => {
    signedInAs(teacherMe, base([payment(3)]))
    renderApp('/payments')

    fireEvent.click(await screen.findByRole('button', { name: 'Reverse' }))
    await screen.findByRole('dialog')

    expect(screen.queryByText(/No money is returned/)).not.toBeInTheDocument()
  })
})
