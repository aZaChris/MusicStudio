import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiFetch } from '../../../api/client'
import type { OnboardingLink, PaymentAccount } from '../../../api/types'

const KEY = ['payment-account']

/**
 * The studio's payment account (owner and teachers). While the feature is switched off the server
 * answers 404 and the page shows nothing; a retry could not change that, so there is none.
 */
export function usePaymentAccount() {
  return useQuery({
    queryKey: KEY,
    queryFn: () => apiFetch<PaymentAccount>('/payment-account/'),
    retry: false,
  })
}

/** Owner only: where to send them on Stripe's own page to open or finish the account. */
export function useStartOnboarding() {
  return useMutation({
    mutationFn: () => apiFetch<OnboardingLink>('/payment-account/onboarding/', { method: 'POST' }),
  })
}

/** Owner only: read the account again from Stripe (when they come back from its page). */
export function useRefreshAccount() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => apiFetch<PaymentAccount>('/payment-account/refresh/', { method: 'POST' }),
    onSuccess: (account) => {
      queryClient.setQueryData(KEY, account)
      // Packages may become payable online (or stop being) with the account state.
      void queryClient.invalidateQueries({ queryKey: ['packages'] })
    },
  })
}

/** Owner only, only for a disconnected account: remove the dead link so they can start again. */
export function useRestartAccount() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => apiFetch<void>('/payment-account/restart/', { method: 'POST' }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: KEY }),
  })
}
