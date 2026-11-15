import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, test, vi, type Mock } from 'vitest'

import { page } from '../../test/fake-api'
import { parentMe, payment, registerSummary, student, teacherMe } from '../../test/fixtures'
import { renderApp, signedInAs } from '../../test/utils'

const routes = (more = {}) => ({
  'GET /payments/': { status: 200, body: page([payment(1)]) },
  'GET /students/': { status: 200, body: page([student(7, { full_name: 'Giulia Rossi' })]) },
  'GET /payments/register/summary/': { status: 200, body: registerSummary() },
  ...more,
})

describe('cash register: period, totals, export', () => {
  beforeEach(() => {
    vi.useFakeTimers({ now: new Date(2026, 10, 15, 12, 0), toFake: ['Date'] })
  })
  afterEach(() => vi.useRealTimers())

  test("shows the server's totals overall and per method for the current month", async () => {
    const api = signedInAs(teacherMe, routes())
    renderApp('/payments')

    const block = await screen.findByLabelText('Totals for the period')
    expect(within(block).getByText('Received').nextElementSibling).toHaveTextContent('€250.00')
    expect(within(block).getByText('Reversed').nextElementSibling).toHaveTextContent('€100.00')
    expect(within(block).getByText('Net').nextElementSibling).toHaveTextContent('€150.00')
    const cash = screen.getAllByText('Cash').find((el) => el.closest('tr') && el.tagName === 'TD')
    expect(within(cash!.closest('tr') as HTMLElement).getAllByText('€100.00').length).toBeGreaterThan(0)
    // The default period is the current local month, filtered by the server.
    const summaryCalls = api.callsTo('GET /payments/register/summary/')
    expect(summaryCalls[0].path).toBe('/payments/register/summary/?date_from=2026-11-01&date_to=2026-11-30')
    expect(api.callsTo('GET /payments/?date_from=2026-11-01&date_to=2026-11-30').length).toBeGreaterThan(0)
  })

  test('changing the period asks the server again', async () => {
    const api = signedInAs(teacherMe, routes())
    renderApp('/payments')
    await screen.findByLabelText('Totals for the period')

    fireEvent.click(screen.getByRole('button', { name: 'Day' }))
    const register = screen.getByRole('region', { name: 'Cash register' })
    fireEvent.change(within(register).getByLabelText('Date'), { target: { value: '2026-11-05' } })

    await waitFor(() =>
      expect(
        api
          .callsTo('GET /payments/register/summary/')
          .some((c) => c.path.endsWith('date_from=2026-11-05&date_to=2026-11-05')),
      ).toBe(true),
    )
  })

  describe('export', () => {
    let click: Mock<() => void>
    beforeEach(() => {
      click = vi.fn<() => void>()
      vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(click)
      vi.stubGlobal('URL', { ...URL, createObjectURL: vi.fn(() => 'blob:x'), revokeObjectURL: vi.fn() })
    })

    test('downloads the CSV for the period through the authenticated client', async () => {
      const api = signedInAs(
        teacherMe,
        routes({ 'GET /payments/register/export/csv/': { status: 200, body: { any: 'file' } } }),
      )
      renderApp('/payments')

      fireEvent.click(await screen.findByRole('button', { name: 'Export CSV' }))

      await waitFor(() => expect(click).toHaveBeenCalledTimes(1))
      const call = api.callsTo('GET /payments/register/export/csv/')[0]
      expect(call.path).toBe('/payments/register/export/csv/?date_from=2026-11-01&date_to=2026-11-30')
      expect(call.authorization).toMatch(/^Bearer /) // the token is a header, never in the URL
      expect(call.path).not.toMatch(/token|bearer/i)
    })

    test('a period over one year cannot be exported and says why', async () => {
      signedInAs(teacherMe, routes())
      renderApp('/payments')
      await screen.findByLabelText('Totals for the period')

      fireEvent.click(screen.getByRole('button', { name: 'Custom period' }))
      fireEvent.change(screen.getByLabelText('From'), { target: { value: '2025-01-01' } })
      fireEvent.change(screen.getByLabelText('To'), { target: { value: '2026-12-31' } })

      expect(await screen.findByText(/Exports cover at most one year/)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Export CSV' })).toBeDisabled()
      expect(screen.getByRole('button', { name: 'Export PDF' })).toBeDisabled()
    })

    test('a server refusal for the period is shown as its translated sentence', async () => {
      signedInAs(
        teacherMe,
        routes({
          'GET /payments/register/export/pdf/': {
            status: 400,
            body: { detail: 'The period cannot be longer than 366 days.', code: 'period_too_long' },
          },
        }),
      )
      renderApp('/payments')

      fireEvent.click(await screen.findByRole('button', { name: 'Export PDF' }))

      expect(await screen.findByText('The period is too long: choose at most one year.')).toBeInTheDocument()
      expect(click).not.toHaveBeenCalled()
    })
  })

  test('an empty period shows zeros, not an error', async () => {
    signedInAs(
      teacherMe,
      routes({
        'GET /payments/': { status: 200, body: page([]) },
        'GET /payments/register/summary/': {
          status: 200,
          body: registerSummary({
            totals: { received: '0.00', reversed: '0.00', net: '0.00' },
            by_method: [],
            counts: { paid: 0, pending: 0, overdue: 0, reversal: 0 },
          }),
        },
      }),
    )
    renderApp('/payments')

    const block = await screen.findByLabelText('Totals for the period')
    expect(within(block).getByText('Net').nextElementSibling).toHaveTextContent('€0.00')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  test('a parent never reaches the register', async () => {
    const api = signedInAs(parentMe, {
      'GET /students/': { status: 200, body: page([student(7)]) },
      'GET /payments/?student=7': { status: 200, body: page([payment(1)]) },
      'GET /students/7/lessons/': { status: 200, body: [] },
    })
    renderApp('/payments')

    await waitFor(() => expect(screen.queryByLabelText('Totals for the period')).not.toBeInTheDocument())
    expect(api.callsTo('GET /payments/register')).toHaveLength(0)
  })
})
