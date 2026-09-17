import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "./api";

export interface Lesson {
  id: number;
  studentId: number;
  studentName: string;
  studentLastName: string;
  teacherId?: number;
  packageId: number | null;
  startTime: string;
  durationMinutes?: number;
  status: "scheduled" | "completed" | "cancelled" | "no_show";
  notes: string;
}

export interface Package {
  id: number;
  studentId: number;
  totalLessons: number;
  lessonsRemaining: number;
  purchaseDate: string;
  expiryDate: string | null;
  price: string;
  status: "active" | "expired" | "completed";
  isLow: boolean;
}

export interface Student {
  id: number;
  firstName: string;
  lastName: string;
  fullName: string;
  instrument: string;
  isActive: boolean;
  activePackage: Package | null;
  paymentStatus: "paid" | "pending" | "overdue" | null;
}

export interface Payment {
  id: number;
  studentId: number;
  studentFirstName: string;
  studentLastName: string;
  packageId: number | null;
  amount: string;
  date: string;
  method: "cash" | "bank_transfer" | "manual_entry";
  status: "paid" | "pending" | "overdue";
}

export interface Dashboard {
  week: Lesson[];
  upcoming: Lesson[];
  pendingPaymentsCount: number;
  activeStudentsCount: number;
  lowPackageStudents: { id: number; fullName: string }[];
}

export function useDashboard() {
  return useQuery({ queryKey: ["dashboard"], queryFn: () => apiFetch<Dashboard>("/dashboard") });
}

export function useStudents() {
  return useQuery({
    queryKey: ["students"],
    queryFn: () => apiFetch<{ results: Student[] }>("/students?is_active=true"),
  });
}

export function useStudent(id: number) {
  return useQuery({
    queryKey: ["students", id],
    queryFn: () => apiFetch<Student>(`/students/${id}`),
    enabled: !!id,
  });
}

export function useStudentLessons(id: number) {
  return useQuery({
    queryKey: ["students", id, "lessons"],
    queryFn: () => apiFetch<Lesson[]>(`/students/${id}/lessons`),
    enabled: !!id,
  });
}

export function usePayments() {
  return useQuery({
    queryKey: ["payments"],
    queryFn: () => apiFetch<{ results: Payment[] }>("/payments"),
  });
}

export function useCompleteLesson() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, note }: { id: number; note?: string }) =>
      apiFetch<Lesson>(`/lessons/${id}/complete`, { method: "POST", body: JSON.stringify({ note: note ?? "" }) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["students"] });
    },
  });
}

export function useRegisterPayment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      student: number;
      amount: string;
      date: string;
      method: Payment["method"];
      status: Payment["status"];
    }) => apiFetch<Payment>("/payments", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["payments"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["students"] });
    },
  });
}
