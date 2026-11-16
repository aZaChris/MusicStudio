import { useMutation } from '@tanstack/react-query'

import { apiFetch } from '../../../api/client'
import type { Checkout } from '../../../api/types'

/**
 * Where to send the payer to pay a package online, on Stripe's own page (the money goes to the
 * studio's account). The server answers 409 when the studio does not take online payments.
 */
export function useStartCheckout() {
  return useMutation({
    mutationFn: (packageId: number) =>
      apiFetch<Checkout>(`/packages/${packageId}/checkout/`, { method: 'POST' }),
  })
}
