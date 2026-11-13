import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, test, vi } from 'vitest'

import { page } from '../../test/fake-api'
import { dashboard, lesson, payment, student, teacherMe } from '../../test/fixtures'
import { renderApp, signedInAs } from '../../test/utils'

describe('dashboard', () => {
  test("shows the server's counts, upcoming lessons and the low-package warning", async () => {
    signedInAs(teacherMe, { 'GET /dashboard/': { status: 200, body: dashboard() } })
    renderApp('/')

    expect(await screen.findByText('12')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText(/Giulia Rossi — Running low/)).toBeInTheDocument()
  })

  test('greets by first name, and the sidebar shows the full name, not the email', async () => {
    signedInAs(teacherMe, { 'GET /dashboard/': { status: 200, body: dashboard() } })
    renderApp('/')

    expect(await screen.findByRole('heading', { name: 'Hi, Mario' })).toBeInTheDocument()
    expect(screen.getByText('Mario Rossi')).toBeInTheDocument()
    expect(screen.queryByText('mario.rossi@example.com')).not.toBeInTheDocument()
  })

  test('falls back to the email when the account has no name', async () => {
    signedInAs(
      { ...teacherMe, first_name: '', last_name: '' },
      { 'GET /dashboard/': { status: 200, body: dashboard() } },
    )
    renderApp('/')

    expect(await screen.findByRole('heading', { name: 'Hi, mario.rossi' })).toBeInTheDocument()
    expect(screen.getByText('mario.rossi@example.com')).toBeInTheDocument()
  })

  test('the home lists the four most recent payments, newest first', async () => {
    signedInAs(teacherMe, {
      'GET /dashboard/': { status: 200, body: dashboard() },
      'GET /payments/': {
        status: 200,
        body: page([
          payment(1, { student_name: 'Oldest One', date: '2026-10-01' }),
          payment(2, { student_name: 'Newest One', date: '2026-11-08' }),
          payment(3, { student_name: 'Middle Two', date: '2026-10-20' }),
          payment(4, { student_name: 'Middle Three', date: '2026-10-25' }),
          payment(5, { student_name: 'Middle Four', date: '2026-10-30' }),
        ]),
      },
    })
    renderApp('/')

    expect(await screen.findByText('Newest One')).toBeInTheDocument()
    const names = screen
      .getAllByRole('row')
      .slice(1)
      .map((r) => within(r).getAllByRole('cell')[0].textContent)
    expect(names).toEqual(['Newest One', 'Middle Four', 'Middle Three', 'Middle Two'])
  })

  test('an empty agenda says so', async () => {
    signedInAs(teacherMe, {
      'GET /dashboard/': {
        status: 200,
        body: dashboard({ week: [], upcoming: [], low_package_students: [] }),
      },
    })
    renderApp('/')

    expect(await screen.findByText('No upcoming lessons.')).toBeInTheDocument()
  })

  test('a 403 is shown at once, without retries', async () => {
    const api = signedInAs(teacherMe, { 'GET /dashboard/': { status: 403, body: { detail: 'No.' } } })
    renderApp('/')

    expect(await screen.findByText('You are not allowed to do this.')).toBeInTheDocument()
    expect(api.callsTo('GET /dashboard/')).toHaveLength(1)
  })

  test('completing a lesson posts the note and refreshes the dashboard', async () => {
    let completed = false
    const api = signedInAs(teacherMe, {
      'GET /dashboard/': () => ({
        status: 200,
        body: dashboard({
          upcoming: completed ? [] : [lesson()],
          week: [lesson({ status: completed ? 'completed' : 'scheduled' })],
        }),
      }),
      'POST /lessons/1/complete/': () => {
        completed = true
        return { status: 200, body: lesson({ status: 'completed' }) }
      },
    })
    renderApp('/')

    fireEvent.click(await screen.findByRole('button', { name: /Giulia Rossi/ }))
    fireEvent.change(screen.getByLabelText('Progress note'), { target: { value: 'Scales in G' } })
    fireEvent.click(screen.getByRole('button', { name: 'Complete' }))

    expect(await screen.findByText('No upcoming lessons.')).toBeInTheDocument()
    expect(api.callsTo('POST /lessons/1/complete/')[0].body).toEqual({ note: 'Scales in G' })
  })

  test("a refused completion keeps the dialog open with the server's reason", async () => {
    signedInAs(teacherMe, {
      'GET /dashboard/': { status: 200, body: dashboard() },
      'POST /lessons/1/complete/': { status: 409, body: { detail: 'Lesson already completed.' } },
    })
    renderApp('/')

    fireEvent.click(await screen.findByRole('button', { name: /Giulia Rossi/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Complete' }))

    const dialog = await screen.findByRole('dialog')
    expect(
      await within(dialog).findByText('The server rejected the request: Lesson already completed.'),
    ).toBeInTheDocument()
  })
})

describe('roster and student detail', () => {
  test('every active student is listed, beyond the first server page', async () => {
    const first = Array.from({ length: 25 }, (_, i) => student(i + 1))
    const rest = Array.from({ length: 5 }, (_, i) => student(i + 26))
    signedInAs(teacherMe, {
      'GET /students/?is_active=true': {
        status: 200,
        body: page(first, 'http://api.internal/api/v1/students/?is_active=true&page=2'),
      },
      'GET /students/?is_active=true&page=2': { status: 200, body: page(rest) },
    })
    renderApp('/students')

    expect(await screen.findByText('Student30 Test')).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: /Student\d+ Test/ })).toHaveLength(30)
  })

  test('no students: a message, not a blank page', async () => {
    signedInAs(teacherMe, { 'GET /students/': { status: 200, body: page([]) } })
    renderApp('/students')

    expect(await screen.findByText('No active students.')).toBeInTheDocument()
  })

  test('detail shows the package and the translated lesson history', async () => {
    signedInAs(teacherMe, {
      'GET /students/7/': { status: 200, body: student(7) },
      'GET /students/7/lessons/': {
        status: 200,
        body: [
          lesson({ id: 1, status: 'completed', notes: 'Good tempo' }),
          lesson({ id: 2, status: 'no_show' }),
        ],
      },
    })
    renderApp('/students/7')

    expect(await screen.findByText('2/10 · Active')).toBeInTheDocument()
    expect(screen.getByText('Completed')).toBeInTheDocument()
    expect(screen.getByText('No-show')).toBeInTheDocument()
    expect(screen.getByText('Good tempo')).toBeInTheDocument()
  })

  test('a student without an active package says so', async () => {
    signedInAs(teacherMe, {
      'GET /students/9/': { status: 200, body: student(9, { active_package: null }) },
      'GET /students/9/lessons/': { status: 200, body: [] },
    })
    renderApp('/students/9')

    expect(await screen.findByText('No active package')).toBeInTheDocument()
    expect(screen.getByText('No lessons yet.')).toBeInTheDocument()
  })

  test("a student that is not visible shows 'not found'", async () => {
    signedInAs(teacherMe, {
      'GET /students/404/': { status: 404, body: { detail: 'Not found.' } },
      'GET /students/404/lessons/': { status: 404, body: { detail: 'Not found.' } },
    })
    renderApp('/students/404')

    expect(await screen.findByText(/Not found\. It may have been removed/)).toBeInTheDocument()
  })
})

describe('payments', () => {
  const routes = (more = {}) => ({
    'GET /payments/': { status: 200, body: page([payment(1)]) },
    'GET /students/': { status: 200, body: page([student(7, { full_name: 'Giulia Rossi' })]) },
    ...more,
  })

  async function fill(amount: string) {
    await screen.findByRole('option', { name: 'Giulia Rossi' }) // options load after the select
    fireEvent.change(screen.getByLabelText('Student'), { target: { value: '7' } })
    fireEvent.change(screen.getByLabelText('Amount'), { target: { value: amount } })
    fireEvent.click(screen.getByRole('radio', { name: 'Bank transfer' }))
    fireEvent.click(screen.getByRole('button', { name: 'Register payment' }))
  }

  test('lists payments with translated method and status and the local date', async () => {
    signedInAs(teacherMe, routes())
    renderApp('/payments')

    // The "Paid" filter chip is on screen before the rows are: wait for a row, then read its cells.
    expect(await screen.findByText('2 Nov 2026')).toBeInTheDocument()
    const row = screen.getAllByRole('row')[1] // [0] is the header
    expect(within(row).getByText('Paid')).toBeInTheDocument()
    expect(within(row).getByText('Bank transfer')).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: 'Bank transfer' })).toBeInTheDocument()
  })

  test("at 00:30 local time the default date is today's local date, not the UTC one", async () => {
    vi.useFakeTimers({ now: new Date(2026, 10, 10, 0, 30), toFake: ['Date'] })
    const api = signedInAs(teacherMe, routes({ 'POST /payments/': { status: 201, body: payment(2) } }))
    renderApp('/payments')

    await fill('80.50')

    await waitFor(() => expect(api.callsTo('POST /payments/')).toHaveLength(1))
    expect(api.callsTo('POST /payments/')[0].body).toEqual({
      student: 7,
      amount: '80.50',
      date: '2026-11-10',
      method: 'bank_transfer',
      status: 'paid',
    })
    expect(await screen.findByText('Payment registered.')).toBeInTheDocument()
  })

  test("a rejected payment shows the server's reason and keeps what was typed", async () => {
    signedInAs(
      teacherMe,
      routes({ 'POST /payments/': { status: 400, body: { amount: ['Too many digits.'] } } }),
    )
    renderApp('/payments')

    await fill('99999999')

    expect(
      await screen.findByText('The server rejected the request: amount: Too many digits.'),
    ).toBeInTheDocument()
    expect(screen.getByLabelText('Amount')).toHaveValue(99999999)
  })
})
