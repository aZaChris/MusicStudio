import { useQuery } from '@tanstack/react-query'

import { apiFetch, fetchAllPages } from '../../../api/client'
import type { Lesson, Student } from '../../../api/types'

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
