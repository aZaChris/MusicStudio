import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiFetch, fetchAllPages } from '../../../api/client'
import type { Payment, PaymentRequest, Reversal } from '../../../api/types'

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

/** Reverse a paid entry: the original stays, a linked reversal is created (never an edit). */
export function useReversePayment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) =>
      apiFetch<Reversal>(`/payments/${id}/reverse/`, { method: 'POST', body: { reason } }),
    onSuccess: () => {
      // A reversal can reopen a package and change the student's payment status.
      for (const key of ['payments', 'dashboard', 'students', 'packages']) {
        void queryClient.invalidateQueries({ queryKey: [key] })
      }
    },
  })
}
