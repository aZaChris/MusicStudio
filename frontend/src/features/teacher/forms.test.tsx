import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, test } from 'vitest'

import { page } from '../../test/fake-api'
import { lesson, student, teacherMe } from '../../test/fixtures'
import { renderApp, signedInAs } from '../../test/utils'

const fill = (label: string, value: string) =>
  fireEvent.change(screen.getByLabelText(label), { target: { value } })

describe('adding a student', () => {
  test('posts the names and opens the new student', async () => {
    const api = signedInAs(teacherMe, {
      'GET /students/': { status: 200, body: page([student(1)]) },
      'POST /students/': { status: 201, body: student(5, { full_name: 'Anna Verdi' }) },
      'GET /students/5/': {
        status: 200,
        body: student(5, { full_name: 'Anna Verdi', active_package: null }),
      },
      'GET /students/5/lessons/': { status: 200, body: [] },
    })
    renderApp('/students')

    fireEvent.click(await screen.findByRole('button', { name: 'New student' }))
    const dialog = await screen.findByRole('dialog')
    fireEvent.change(within(dialog).getByLabelText('First name'), { target: { value: ' Anna ' } })
    fill('Last name', 'Verdi')
    fill('Instrument', 'Violin')
    fireEvent.click(within(dialog).getByRole('button', { name: 'Save' }))

    await waitFor(() => expect(api.callsTo('POST /students/')).toHaveLength(1))
    // Names are trimmed before they leave the browser.
    expect(api.callsTo('POST /students/')[0].body).toEqual({
      first_name: 'Anna',
      last_name: 'Verdi',
      instrument: 'Violin',
    })
    expect(await screen.findByRole('heading', { name: 'Anna Verdi' })).toBeInTheDocument()
  })

  test("a refusal keeps the dialog open with the server's reason", async () => {
    signedInAs(teacherMe, {
      'GET /students/': { status: 200, body: page([]) },
      'POST /students/': { status: 400, body: { instrument: ['This field may not be blank.'] } },
    })
    renderApp('/students')

    fireEvent.click(await screen.findByRole('button', { name: 'New student' }))
    fill('First name', 'Anna')
    fill('Last name', 'Verdi')
    fill('Instrument', 'x')
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    const dialog = await screen.findByRole('dialog')
    expect(await within(dialog).findByText(/instrument: This field may not be blank/)).toBeInTheDocument()
  })
})

describe('a student page', () => {
  const routes = (more = {}) => ({
    'GET /students/7/': {
      status: 200,
      body: student(7, { first_name: 'Giulia', last_name: 'Rossi', full_name: 'Giulia Rossi' }),
    },
    'GET /students/7/lessons/': { status: 200, body: [lesson({ id: 4, notes: '' })] },
    ...more,
  })

  test('sells a package with the date and the price as typed', async () => {
    const api = signedInAs(teacherMe, routes({ 'POST /packages/': { status: 201, body: { id: 9 } } }))
    renderApp('/students/7')

    fireEvent.click(await screen.findByRole('button', { name: 'New package' }))
    fill('Number of lessons', '8')
    fill('Price (€)', '180,50')
    fill('Purchase date', '2026-11-10')
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Save' }))

    await waitFor(() => expect(api.callsTo('POST /packages/')).toHaveLength(1))
    expect(api.callsTo('POST /packages/')[0].body).toEqual({
      student: 7,
      total_lessons: 8,
      price: '180.50', // the decimal comma becomes a point
      purchase_date: '2026-11-10',
      expiry_date: null,
    })
  })

  test('schedules a lesson at the local wall-clock time', async () => {
    const api = signedInAs(teacherMe, routes({ 'POST /lessons/': { status: 201, body: lesson({ id: 5 }) } }))
    renderApp('/students/7')

    fireEvent.click(await screen.findByRole('button', { name: 'Schedule a lesson' }))
    fill('Day', '2026-11-12')
    fill('Time', '16:30')
    fill('Duration (minutes)', '60')
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Save' }))

    await waitFor(() => expect(api.callsTo('POST /lessons/')).toHaveLength(1))
    const sent = api.callsTo('POST /lessons/')[0].body as {
      start_time: string
      duration_minutes: number
      student: number
    }
    // 16:30 in Rome (UTC+1 in November) is 15:30 UTC; the test runs with TZ=Europe/Rome.
    expect(sent.start_time).toBe('2026-11-12T15:30:00.000Z')
    expect(sent).toMatchObject({ student: 7, duration_minutes: 60 })
  })

  test('an overlapping lesson shows the 409 reason and stays open', async () => {
    signedInAs(
      teacherMe,
      routes({
        'POST /lessons/': { status: 409, body: { detail: 'Overlaps another lesson.', code: 'conflict' } },
      }),
    )
    renderApp('/students/7')

    fireEvent.click(await screen.findByRole('button', { name: 'Schedule a lesson' }))
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Save' }))

    expect(await screen.findByText(/Overlaps another lesson/)).toBeInTheDocument()
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  test('a scheduled lesson can be cancelled or marked as a no-show', async () => {
    const api = signedInAs(
      teacherMe,
      routes({ 'POST /lessons/4/cancel/': { status: 200, body: lesson({ id: 4, status: 'no_show' }) } }),
    )
    renderApp('/students/7')

    fireEvent.click(await screen.findByRole('button', { name: 'Mark no-show' }))

    await waitFor(() => expect(api.callsTo('POST /lessons/4/cancel/')).toHaveLength(1))
    expect(api.callsTo('POST /lessons/4/cancel/')[0].body).toEqual({ status: 'no_show' })
  })

  test('editing can archive the student', async () => {
    const api = signedInAs(
      teacherMe,
      routes({ 'PATCH /students/7/': { status: 200, body: student(7, { is_active: false }) } }),
    )
    renderApp('/students/7')

    fireEvent.click(await screen.findByRole('button', { name: 'Edit' }))
    expect(screen.getByLabelText('First name')).toHaveValue('Giulia')
    fireEvent.click(screen.getByLabelText(/Active student/))
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Save' }))

    await waitFor(() => expect(api.callsTo('PATCH /students/7/')).toHaveLength(1))
    expect(api.callsTo('PATCH /students/7/')[0].body).toMatchObject({ is_active: false })
  })
})
