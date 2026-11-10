import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiFetch } from '../../../api/client'
import type { Dashboard, Lesson, LessonCancelStatus, LessonRequest } from '../../../api/types'

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

export function useCreateLesson() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: LessonRequest) => apiFetch<Lesson>('/lessons/', { method: 'POST', body: data }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      void queryClient.invalidateQueries({ queryKey: ['students'] })
    },
  })
}

/** Cancel a lesson, or mark the student as a no-show. */
export function useCancelLesson() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, status }: { id: number; status: LessonCancelStatus }) =>
      apiFetch<Lesson>(`/lessons/${id}/cancel/`, { method: 'POST', body: { status } }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      void queryClient.invalidateQueries({ queryKey: ['students'] })
    },
  })
}
