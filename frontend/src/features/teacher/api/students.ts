import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiFetch } from '../../../api/client'
import type { Lesson } from './lessons'

export interface Package {
  id: number
  student: number
  total_lessons: number
  lessons_remaining: number
  purchase_date: string
  expiry_date: string | null
  price: string
  status: 'active' | 'expired' | 'completed'
  is_low: boolean
}

export interface Student {
  id: number
  first_name: string
  last_name: string
  full_name: string
  instrument: string
  teacher: number
  is_active: boolean
  active_package: Package | null
  payment_status: 'paid' | 'pending' | 'overdue' | null
}

interface Paginated<T> {
  results: T[]
  count: number
}

export function useStudents() {
  return useQuery({
    queryKey: ['students'],
    queryFn: () => apiFetch<Paginated<Student>>('/students/?is_active=true'),
  })
}

export function useStudent(id: number) {
  return useQuery({
    queryKey: ['students', id],
    queryFn: () => apiFetch<Student>(`/students/${id}/`),
    enabled: !!id,
  })
}

export function useStudentLessons(id: number) {
  return useQuery({
    queryKey: ['students', id, 'lessons'],
    queryFn: () => apiFetch<Lesson[]>(`/students/${id}/lessons/`),
    enabled: !!id,
  })
}

export function useCreatePackage() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: {
      student: number
      total_lessons: number
      purchase_date: string
      price: string
      expiry_date?: string
    }) => apiFetch<Package>('/packages/', { method: 'POST', body: JSON.stringify(data) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['students'] }),
  })
}
