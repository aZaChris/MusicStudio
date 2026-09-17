import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { renderWithProviders } from '../../test/utils'
import { Dashboard } from './Dashboard'

describe('Dashboard', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            week: [],
            upcoming: [],
            pending_payments_count: 2,
            active_students_count: 5,
            low_package_students: [],
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        ),
      ),
    )
  })

  it('renders the weekly overview once data loads', async () => {
    render(renderWithProviders(<Dashboard />))

    expect(await screen.findByText('This week')).toBeInTheDocument()
    expect(await screen.findByText('5')).toBeInTheDocument()
    expect(await screen.findByText('2')).toBeInTheDocument()
  })
})
