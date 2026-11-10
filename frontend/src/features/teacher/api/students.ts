import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiFetch, fetchAllPages } from '../../../api/client'
import type { Lesson, Student, StudentRequest } from '../../../api/types'

/** Every active student, all pages (not only the first 25). */
export function useStudents() {
  return useQuery({
    queryKey: ['students'],
    queryFn: () => fetchAllPages<Student>('/students/?is_active=true'),
  })
}

export function useStudent(id: number) {
  return useQuery({
    queryKey: ['students', id],
    queryFn: () => apiFetch<Student>(`/students/${id}/`),
    enabled: id > 0,
  })
}

export function useStudentLessons(id: number) {
  return useQuery({
    queryKey: ['students', id, 'lessons'],
    queryFn: () => apiFetch<Lesson[]>(`/students/${id}/lessons/`),
    enabled: id > 0,
  })
}

/** What changes when a student is added or edited: the list, the detail and the home counters. */
function useRefreshStudents() {
  const queryClient = useQueryClient()
  return () => {
    void queryClient.invalidateQueries({ queryKey: ['students'] })
    void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
  }
}

export function useCreateStudent() {
  const refresh = useRefreshStudents()
  return useMutation({
    mutationFn: (data: StudentRequest) => apiFetch<Student>('/students/', { method: 'POST', body: data }),
    onSuccess: refresh,
  })
}

export function useUpdateStudent(id: number) {
  const refresh = useRefreshStudents()
  return useMutation({
    mutationFn: (data: Partial<StudentRequest>) =>
      apiFetch<Student>(`/students/${id}/`, { method: 'PATCH', body: data }),
    onSuccess: refresh,
  })
}
