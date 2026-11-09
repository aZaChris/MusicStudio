// Server state hooks on the Django API. Shapes are the generated contract types.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch, fetchAllPages } from "./api/client";
import type { Dashboard, Lesson, Payment, PaymentRequest, Student } from "./api/types";

export function useDashboard() {
  return useQuery({ queryKey: ["dashboard"], queryFn: () => apiFetch<Dashboard>("/dashboard/") });
}

/** Every active student, all pages (audit issue 8). */
export function useStudents() {
  return useQuery({
    queryKey: ["students"],
    queryFn: () => fetchAllPages<Student>("/students/?is_active=true"),
  });
}

export function useStudent(id: number) {
  return useQuery({
    queryKey: ["students", id],
    queryFn: () => apiFetch<Student>(`/students/${id}/`),
    enabled: id > 0,
  });
}

export function useStudentLessons(id: number) {
  return useQuery({
    queryKey: ["students", id, "lessons"],
    queryFn: () => apiFetch<Lesson[]>(`/students/${id}/lessons/`),
    enabled: id > 0,
  });
}

/** Payments, optionally of one student (filtered by the server, not on the phone). */
export function usePayments(studentId?: number) {
  return useQuery({
    queryKey: ["payments", studentId ?? "all"],
    queryFn: () => fetchAllPages<Payment>(studentId ? `/payments/?student=${studentId}` : "/payments/"),
    enabled: studentId === undefined || studentId > 0,
  });
}

export function useCompleteLesson() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, note }: { id: number; note: string }) =>
      apiFetch<Lesson>(`/lessons/${id}/complete/`, { method: "POST", body: { note } }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      void queryClient.invalidateQueries({ queryKey: ["students"] });
    },
  });
}

export function useRegisterPayment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: PaymentRequest) => apiFetch<Payment>("/payments/", { method: "POST", body: data }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["payments"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      void queryClient.invalidateQueries({ queryKey: ["students"] });
    },
  });
}
