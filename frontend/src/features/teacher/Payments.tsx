import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { Sidebar } from '../../components/Sidebar'
import { useRegisterPayment, usePayments, type Payment } from './api/payments'
import { useStudents } from './api/students'

export function Payments() {
  const { t } = useTranslation()
  const { data } = usePayments()
  const { data: students } = useStudents()
  const registerPayment = useRegisterPayment()

  const [studentId, setStudentId] = useState('')
  const [amount, setAmount] = useState('')
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [method, setMethod] = useState<Payment['method']>('cash')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!studentId || !amount) return
    await registerPayment.mutateAsync({
      student: Number(studentId),
      amount,
      date,
      method,
      status: 'paid',
    })
    setAmount('')
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar />
      <div style={{ flex: 1, padding: '36px 44px', maxWidth: 1280, display: 'flex', flexDirection: 'column', gap: 24 }}>
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
            {t('roster.student')}
            <select value={studentId} onChange={(e) => setStudentId(e.target.value)} required>
              <option value="" />
              {students?.results.map((s) => (
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
            <select value={method} onChange={(e) => setMethod(e.target.value as Payment['method'])}>
              <option value="cash">cash</option>
              <option value="bank_transfer">bank_transfer</option>
              <option value="manual_entry">manual_entry</option>
            </select>
          </label>
          <button type="submit" disabled={registerPayment.isPending}>
            {t('payments.registerPayment')}
          </button>
        </form>

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
            {data?.results.map((payment) => (
              <tr key={payment.id} style={{ borderTop: '1px solid var(--ms-border)', fontSize: 14 }}>
                <td style={{ padding: '10px 8px' }}>{payment.student_name}</td>
                <td style={{ padding: '10px 8px' }}>{payment.amount}</td>
                <td style={{ padding: '10px 8px' }}>{payment.date}</td>
                <td style={{ padding: '10px 8px' }}>
                  {t(`payments.status${payment.status.charAt(0).toUpperCase()}${payment.status.slice(1)}`)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
