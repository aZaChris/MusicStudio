import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import type { PaymentMethod } from '../../api/types'
import { ErrorText, QueryState } from '../../components/QueryState'
import { Sidebar } from '../../components/Sidebar'
import { formatDay, localDateISO } from '../../lib/dates'
import { useRegisterPayment, usePayments } from './api/payments'
import { useStudents } from './api/students'

// Online card payments come from Stripe webhooks, never from this form.
const MANUAL_METHODS: PaymentMethod[] = ['cash', 'bank_transfer', 'manual_entry']

export function Payments() {
  const { t, i18n } = useTranslation()
  const payments = usePayments()
  const { data: students } = useStudents()
  const registerPayment = useRegisterPayment()

  const [studentId, setStudentId] = useState('')
  const [amount, setAmount] = useState('')
  // Local calendar date: after midnight in Italy the UTC date is still yesterday.
  const [date, setDate] = useState(() => localDateISO())
  const [method, setMethod] = useState<PaymentMethod>('cash')

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!studentId || !amount) return
    registerPayment.mutate(
      { student: Number(studentId), amount, date, method, status: 'paid' },
      { onSuccess: () => setAmount('') }, // on failure the form keeps what was typed
    )
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar />
      <div
        style={{
          flex: 1,
          padding: '36px 44px',
          maxWidth: 1280,
          display: 'flex',
          flexDirection: 'column',
          gap: 24,
        }}
      >
        <h1 style={{ fontFamily: 'var(--ms-font-heading)', fontSize: 22, fontWeight: 600 }}>
          {t('payments.title')}
        </h1>

        <form
          onSubmit={handleSubmit}
          style={{
            display: 'flex',
            gap: 8,
            alignItems: 'flex-end',
            border: '1px solid var(--ms-border)',
            borderRadius: 'var(--ms-radius-lg)',
            padding: 16,
          }}
        >
          <label>
            {t('payments.student')}
            <select value={studentId} onChange={(e) => setStudentId(e.target.value)} required>
              <option value="" />
              {students?.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.full_name}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t('payments.amount')}
            <input
              type="number"
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              required
            />
          </label>
          <label>
            {t('payments.date')}
            <input type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
          </label>
          <label>
            {t('payments.method')}
            <select value={method} onChange={(e) => setMethod(e.target.value as PaymentMethod)}>
              {MANUAL_METHODS.map((m) => (
                <option key={m} value={m}>
                  {t(`payments.methodName.${m}`)}
                </option>
              ))}
            </select>
          </label>
          <button type="submit" disabled={registerPayment.isPending}>
            {t('payments.registerPayment')}
          </button>
        </form>
        <ErrorText error={registerPayment.error} />
        {registerPayment.isSuccess && !amount && <p role="status">{t('payments.saved')}</p>}

        <QueryState
          query={payments}
          isEmpty={(payments.data ?? []).length === 0}
          emptyText={t('payments.empty')}
        >
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ textAlign: 'left', fontSize: 12.5, color: 'var(--ms-text-muted)' }}>
                <th style={{ padding: '10px 8px' }}>{t('roster.student')}</th>
                <th style={{ padding: '10px 8px' }}>{t('payments.amount')}</th>
                <th style={{ padding: '10px 8px' }}>{t('payments.date')}</th>
                <th style={{ padding: '10px 8px' }}>{t('payments.status')}</th>
              </tr>
            </thead>
            <tbody>
              {payments.data?.map((payment) => (
                <tr key={payment.id} style={{ borderTop: '1px solid var(--ms-border)', fontSize: 14 }}>
                  <td style={{ padding: '10px 8px' }}>{payment.student_name}</td>
                  <td style={{ padding: '10px 8px' }}>{payment.amount}</td>
                  <td style={{ padding: '10px 8px' }}>{formatDay(payment.date, i18n.language)}</td>
                  <td style={{ padding: '10px 8px' }}>
                    {payment.status ? t(`payments.statusName.${payment.status}`) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </QueryState>
      </div>
    </div>
  )
}
