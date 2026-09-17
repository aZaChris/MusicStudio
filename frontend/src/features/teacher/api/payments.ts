import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiFetch } from '../../../api/client'

export interface Payment {
  id: number
  student: number
  student_name: string
  package: number | null
  amount: string
  date: string
  method: 'cash' | 'bank_transfer' | 'manual_entry'
  status: 'paid' | 'pending' | 'overdue'
}

interface Paginated<T> {
  results: T[]
}

export function usePayments() {
  return useQuery({
    queryKey: ['payments'],
    queryFn: () => apiFetch<Paginated<Payment>>('/payments/'),
  })
}

export function useRegisterPayment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: {
      student: number
      package?: number
      amount: string
      date: string
      method: Payment['method']
      status: Payment['status']
    }) => apiFetch<Payment>('/payments/', { method: 'POST', body: JSON.stringify(data) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['payments'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['students'] })
    },
  })
}
