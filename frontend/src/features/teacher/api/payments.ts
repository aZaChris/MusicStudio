import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiDownload, apiFetch, fetchAllPages } from '../../../api/client'
import type { Payment, PaymentRequest, Receipt, RegisterSummary, Reversal } from '../../../api/types'
import { saveBlob } from '../../../lib/download'
import { isValidPeriod, type Period } from '../../../lib/period'

const periodQuery = (period: Period) =>
  new URLSearchParams({ date_from: period.from, date_to: period.to }).toString()

/** Payments, or one student's, optionally for a period (filtered by the server, not in the browser). */
export function usePayments(studentId?: number, period?: Period) {
  return useQuery({
    queryKey: ['payments', studentId ?? 'all', period?.from ?? null, period?.to ?? null],
    queryFn: () => {
      const query = new URLSearchParams()
      if (studentId) query.set('student', String(studentId))
      if (period) {
        query.set('date_from', period.from)
        query.set('date_to', period.to)
      }
      const text = query.toString()
      return fetchAllPages<Payment>(text ? `/payments/?${text}` : '/payments/')
    },
    enabled: (studentId === undefined || studentId > 0) && (!period || isValidPeriod(period)),
  })
}

/** Received, reversed and net for a period, overall and per method (computed by the server). */
export function useRegisterSummary(period: Period) {
  return useQuery({
    queryKey: ['payments', 'summary', period.from, period.to],
    queryFn: () => apiFetch<RegisterSummary>(`/payments/register/summary/?${periodQuery(period)}`),
    enabled: isValidPeriod(period),
  })
}

/** Export the period as CSV or PDF through the authenticated client, then save the file. */
export function useExportRegister() {
  return useMutation({
    mutationFn: async ({ kind, period }: { kind: 'csv' | 'pdf'; period: Period }) => {
      const { blob, filename } = await apiDownload(
        `/payments/register/export/${kind}/?${periodQuery(period)}`,
      )
      saveBlob(blob, filename)
    },
  })
}

export function useRegisterPayment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: PaymentRequest) => apiFetch<Payment>('/payments/', { method: 'POST', body: data }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['payments'] })
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      void queryClient.invalidateQueries({ queryKey: ['students'] })
    },
  })
}

/** Reverse a paid entry: the original stays, a linked reversal is created (never an edit). */
export function useReversePayment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) =>
      apiFetch<Reversal>(`/payments/${id}/reverse/`, { method: 'POST', body: { reason } }),
    onSuccess: () => {
      // A reversal can reopen a package and change the student's payment status.
      for (const key of ['payments', 'dashboard', 'students', 'packages']) {
        void queryClient.invalidateQueries({ queryKey: [key] })
      }
    },
  })
}

/**
 * Issue the receipt of a paid entry (the server answers with the existing one on a repeat, same
 * number) and save its PDF. The language is the portal's: it is kept from the first issue.
 */
export function useIssueReceipt() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ paymentId, language }: { paymentId: number; language: 'it' | 'en' }) => {
      const receipt = await apiFetch<Receipt>(`/payments/${paymentId}/receipt/`, {
        method: 'POST',
        body: { language },
      })
      const { blob, filename } = await apiDownload(`/receipts/${receipt.id}/pdf/`)
      saveBlob(blob, filename)
      return receipt
    },
    // The payment list now shows the receipt number.
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['payments'] }),
  })
}

/** Issued receipts of one student (a family sees only its own children's). */
export function useReceipts(studentId: number) {
  return useQuery({
    queryKey: ['receipts', studentId],
    queryFn: () => fetchAllPages<Receipt>(`/receipts/?student=${studentId}`),
    enabled: studentId > 0,
  })
}

/** Save one receipt's PDF through the authenticated client. */
export function useDownloadReceipt() {
  return useMutation({
    mutationFn: async (receiptId: number) => {
      const { blob, filename } = await apiDownload(`/receipts/${receiptId}/pdf/`)
      saveBlob(blob, filename)
    },
  })
}
