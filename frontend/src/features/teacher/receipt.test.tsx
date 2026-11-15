import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, test, vi, type Mock } from 'vitest'

import { page } from '../../test/fake-api'
import { payment, receipt, registerSummary, student, teacherMe } from '../../test/fixtures'
import { renderApp, signedInAs } from '../../test/utils'

const routes = (list: ReturnType<typeof payment>[], more = {}) => ({
  'GET /payments/': { status: 200, body: page(list) },
  'GET /students/': { status: 200, body: page([student(7, { full_name: 'Giulia Rossi' })]) },
  'GET /payments/register/summary/': { status: 200, body: registerSummary() },
  ...more,
})

describe('receipts in the register', () => {
  let click: Mock<() => void>
  beforeEach(() => {
    vi.useFakeTimers({ now: new Date(2026, 10, 15, 12, 0), toFake: ['Date'] })
    click = vi.fn<() => void>()
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(click)
    vi.stubGlobal('URL', { ...URL, createObjectURL: vi.fn(() => 'blob:x'), revokeObjectURL: vi.fn() })
  })
  afterEach(() => vi.useRealTimers())

  test('issues the receipt in the portal language, then downloads its PDF', async () => {
    const api = signedInAs(
      teacherMe,
      routes([payment(3)], {
        'POST /payments/3/receipt/': { status: 201, body: receipt(5, { number: '2026-0001' }) },
        'GET /receipts/5/pdf/': { status: 200, body: { any: 'pdf' } },
      }),
    )
    renderApp('/payments')

    fireEvent.click(await screen.findByRole('button', { name: 'Receipt' }))

    await waitFor(() => expect(click).toHaveBeenCalledTimes(1))
    expect(api.callsTo('POST /payments/3/receipt/')[0].body).toEqual({ language: 'en' })
    expect(api.callsTo('GET /receipts/5/pdf/')).toHaveLength(1)
  })

  test('an entry that already has a receipt shows its number', async () => {
    signedInAs(teacherMe, routes([payment(3, { receipt_number: '2026-0007' })]))
    renderApp('/payments')

    expect(await screen.findByRole('button', { name: 'Receipt 2026-0007' })).toBeInTheDocument()
  })

  test('only paid entries offer a receipt', async () => {
    signedInAs(teacherMe, routes([payment(3, { status: 'pending', student_name: 'Anna Neri' }), payment(4)]))
    renderApp('/payments')

    await screen.findByText('Anna Neri')
    expect(screen.getAllByRole('button', { name: 'Receipt' })).toHaveLength(1)
  })

  test('a refusal from the server shows its translated sentence', async () => {
    signedInAs(
      teacherMe,
      routes([payment(3)], {
        'POST /payments/3/receipt/': {
          status: 409,
          body: { detail: 'Only a paid entry has a receipt.', code: 'not_paid' },
        },
      }),
    )
    renderApp('/payments')

    fireEvent.click(await screen.findByRole('button', { name: 'Receipt' }))

    expect(
      await screen.findByText('Only a paid entry can be reversed or have a receipt.'),
    ).toBeInTheDocument()
    expect(click).not.toHaveBeenCalled()
  })
})
