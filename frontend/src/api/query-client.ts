import { QueryClient } from '@tanstack/react-query'

import { isClientError } from './errors'

/**
 * A 401/403/404/409 will not change by asking again: no retry. Network errors and 5xx get at
 * most two retries. Writes are never retried (a payment must not be registered twice).
 */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: (failures, error) => !isClientError(error) && failures < 2 },
      mutations: { retry: false },
    },
  })
}
