import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiFetch } from '../../../api/client'
import type { OpenInstructions, PaymentInstructions, PaymentInstructionsRequest } from '../../../api/types'

/** The studio's payment instructions (owner and teachers; the studio comes from the session). */
export function useInstructions() {
  return useQuery({
    queryKey: ['instructions'],
    queryFn: () => apiFetch<PaymentInstructions>('/payment-instructions/'),
  })
}

/** Replace them (owner only). An all-empty body removes the instructions. */
export function useSaveInstructions() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: PaymentInstructionsRequest) =>
      apiFetch<PaymentInstructions>('/payment-instructions/', { method: 'PUT', body: data }),
    onSuccess: (saved) => {
      queryClient.setQueryData(['instructions'], saved)
      void queryClient.invalidateQueries({ queryKey: ['instructions', 'open'] })
    },
  })
}

/** For a parent or an adult student: instructions of each studio with an open package. */
export function useOpenInstructions() {
  return useQuery({
    queryKey: ['instructions', 'open'],
    queryFn: () => apiFetch<OpenInstructions[]>('/payment-instructions/open/'),
  })
}
