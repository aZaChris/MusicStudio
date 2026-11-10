import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiFetch } from '../../../api/client'
import type { Dashboard, Lesson } from '../../../api/types'

export function useDashboard() {
  return useQuery({ queryKey: ['dashboard'], queryFn: () => apiFetch<Dashboard>('/dashboard/') })
}

export function useCompleteLesson() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, note }: { id: number; note: string }) =>
      apiFetch<Lesson>(`/lessons/${id}/complete/`, { method: 'POST', body: { note } }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      void queryClient.invalidateQueries({ queryKey: ['students'] })
    },
  })
}
