import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiFetch } from '../../../api/client'

export interface Lesson {
  id: number
  student: number
  student_name: string
  teacher: number
  package: number | null
  start_time: string
  duration_minutes: number
  status: 'scheduled' | 'completed' | 'cancelled' | 'no_show'
  notes: string
}

export interface DashboardData {
  week: Lesson[]
  upcoming: Lesson[]
  pending_payments_count: number
  active_students_count: number
  low_package_students: { id: number; full_name: string }[]
}

export function useDashboard() {
  return useQuery({
    queryKey: ['dashboard'],
    queryFn: () => apiFetch<DashboardData>('/dashboard/'),
  })
}

export function useCompleteLesson() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, note }: { id: number; note?: string }) =>
      apiFetch<Lesson>(`/lessons/${id}/complete/`, {
        method: 'POST',
        body: JSON.stringify({ note: note ?? '' }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['students'] })
    },
  })
}
