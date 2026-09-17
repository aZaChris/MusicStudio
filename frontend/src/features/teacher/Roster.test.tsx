import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { renderWithProviders } from '../../test/utils'
import { Roster } from './Roster'

describe('Roster', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(
          JSON.stringify({
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
                active_package: {
                  id: 1,
                  student: 1,
                  total_lessons: 8,
                  lessons_remaining: 1,
                  purchase_date: '2026-01-01',
                  expiry_date: null,
                  price: '150.00',
                  status: 'active',
                  is_low: true,
                },
                payment_status: 'paid',
              },
            ],
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        ),
      ),
    )
  })

  it('renders the student roster with a low-package flag', async () => {
    render(renderWithProviders(<Roster />))

    expect(await screen.findByText('Sara Neri')).toBeInTheDocument()
    expect(await screen.findByText('1/8')).toBeInTheDocument()
    expect(await screen.findByText('Running low')).toBeInTheDocument()
  })
})
