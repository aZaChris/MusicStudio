import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { renderWithProviders } from '../../test/utils'
import { ParentPortal } from './ParentPortal'

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('ParentPortal', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input)
        if (url.includes('/lessons/')) {
          return jsonResponse([
            {
              id: 1,
              student: 1,
              student_name: 'Sara Neri',
              teacher: 1,
              package: 1,
              start_time: '2026-02-01T10:00:00Z',
              duration_minutes: 30,
              status: 'completed',
              notes: 'Great progress',
            },
          ])
        }
        if (url.includes('/payments/')) {
          return jsonResponse({
            results: [
              {
                id: 1,
                student: 1,
                student_name: 'Sara Neri',
                package: 1,
                amount: '50.00',
                date: '2026-01-15',
                method: 'cash',
                status: 'paid',
              },
            ],
          })
        }
        // /students/
        return jsonResponse({
          count: 1,
          results: [
            {
              id: 1,
              first_name: 'Sara',
              last_name: 'Neri',
              full_name: 'Sara Neri',
              instrument: 'Violino',
              teacher: 1,
              is_active: true,
              active_package: null,
              payment_status: 'paid',
            },
          ],
        })
      }),
    )
  })

  it('renders only the linked student, read-only', async () => {
    render(renderWithProviders(<ParentPortal />))

    expect(await screen.findByText('Great progress')).toBeInTheDocument()
    expect(await screen.findByText('50.00')).toBeInTheDocument()
    // read-only: no write controls anywhere on the page
    expect(screen.queryByRole('button', { name: /register/i })).not.toBeInTheDocument()
  })
})
