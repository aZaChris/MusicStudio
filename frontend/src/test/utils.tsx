import { QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import '../i18n'
import { session } from '../api/client'
import { createQueryClient } from '../api/query-client'
import type { Me } from '../api/types'
import App from '../App'
import { AuthProvider } from '../auth/AuthProvider'
import { ThemeProvider } from '../theme/ThemeProvider'
import { installFakeApi, type FakeApi } from './fake-api'

/** The real app (routes, providers, auth) at `path`, with a fresh query cache. */
export function renderApp(path: string) {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <ThemeProvider>
        <MemoryRouter initialEntries={[path]}>
          <AuthProvider>
            <App />
          </AuthProvider>
        </MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>,
  )
}

/** A stored session that the page-load check (/auth/me/) confirms as `me`. */
export function signedInAs(me: Me, routes: Parameters<typeof installFakeApi>[0] = {}): FakeApi {
  session.start({ access: 'access-1', refresh: 'refresh-1' })
  return installFakeApi({ 'GET /auth/me/': { status: 200, body: me }, ...routes })
}
