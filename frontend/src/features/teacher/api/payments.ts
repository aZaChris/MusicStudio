import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiFetch, fetchAllPages } from '../../../api/client'
import type { Payment, PaymentRequest } from '../../../api/types'

/** All payments, or one student's (filtered by the server, not in the browser). */
export function usePayments(studentId?: number) {
  return useQuery({
    queryKey: ['payments', studentId ?? 'all'],
    queryFn: () => fetchAllPages<Payment>(studentId ? `/payments/?student=${studentId}` : '/payments/'),
    enabled: studentId === undefined || studentId > 0,
  })
}

export function useRegisterPayment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: PaymentRequest) => apiFetch<Payment>('/payments/', { method: 'POST', body: data }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['payments'] })
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      void queryClient.invalidateQueries({ queryKey: ['students'] })
    },
  })
}
