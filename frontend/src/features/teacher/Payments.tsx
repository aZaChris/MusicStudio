import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import type { PaymentMethod } from '../../api/types'
import { AppShell } from '../../components/AppShell'
import { ErrorText, QueryState } from '../../components/QueryState'
import { Icon, StatusChip } from '../../components/ui'
import { paymentTone } from '../../components/tones'
import { formatDay, localDateISO } from '../../lib/dates'
import { useRegisterPayment, usePayments } from './api/payments'
import { useStudents } from './api/students'

// Online card payments come from Stripe webhooks, never from this form.
const MANUAL_METHODS: PaymentMethod[] = ['cash', 'bank_transfer', 'manual_entry']

type Filter = 'all' | 'pending' | 'paid'
const FILTERS: Filter[] = ['all', 'pending', 'paid']

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
  const [filter, setFilter] = useState<Filter>('all')

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!studentId || !amount) return
    registerPayment.mutate(
      { student: Number(studentId), amount, date, method, status: 'paid' },
      { onSuccess: () => setAmount('') }, // on failure the form keeps what was typed
    )
  }

  const all = payments.data ?? []
  const toCollect = all.filter((p) => p.status !== 'paid').length
  const shown = all.filter(
    (p) => filter === 'all' || (filter === 'paid' ? p.status === 'paid' : p.status !== 'paid'),
  )
  const money = new Intl.NumberFormat(i18n.language.startsWith('it') ? 'it-IT' : 'en-GB', {
    style: 'currency',
    currency: 'EUR',
  })

  return (
    <AppShell>
      <div className="page-head__text">
        <span className="page-eyebrow">{t('payments.toCollect', { count: toCollect })}</span>
        <h1 className="page-title">{t('payments.title')}</h1>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 20, alignItems: 'flex-start' }}>
        <section className="panel" style={{ flex: '999 1 520px', minWidth: 0, gap: 16 }}>
          <div className="ms-filters">
            {FILTERS.map((f) => (
              <button
                key={f}
                type="button"
                className="ms-filter"
                aria-pressed={filter === f}
                onClick={() => setFilter(f)}
              >
                {t(`payments.filter.${f}`)}
              </button>
            ))}
          </div>
          <QueryState query={payments} isEmpty={all.length === 0} emptyText={t('payments.empty')}>
            <div className="ms-table-wrap">
              <table className="ms-table">
                <thead>
                  <tr>
                    <th scope="col">{t('roster.student')}</th>
                    <th scope="col">{t('payments.date')}</th>
                    <th scope="col">{t('payments.method')}</th>
                    <th scope="col" style={{ textAlign: 'right' }}>
                      {t('payments.amount')}
                    </th>
                    <th scope="col" style={{ textAlign: 'right' }}>
                      {t('payments.status')}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {shown.map((payment) => (
                    <tr key={payment.id}>
                      <td>{payment.student_name}</td>
                      <td>{formatDay(payment.date, i18n.language)}</td>
                      <td>{payment.method ? t(`payments.methodName.${payment.method}`) : '—'}</td>
                      <td className="num">{money.format(Number(payment.amount))}</td>
                      <td style={{ textAlign: 'right' }}>
                        {payment.status ? (
                          <StatusChip tone={paymentTone(payment.status)} small>
                            {t(`payments.statusName.${payment.status}`)}
                          </StatusChip>
                        ) : (
                          '—'
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </QueryState>
        </section>

        <form
          className="panel panel--accent ms-form"
          style={{ flex: '1 1 320px', minWidth: 0 }}
          onSubmit={handleSubmit}
        >
          <h2 className="section-title">{t('payments.registerPayment')}</h2>
          <label className="ms-field">
            {t('payments.student')}
            <select
              className="ms-input"
              value={studentId}
              onChange={(e) => setStudentId(e.target.value)}
              required
            >
              <option value="" />
              {students?.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.full_name}
                </option>
              ))}
            </select>
          </label>
          <div className="ms-form__grid">
            <label className="ms-field">
              {t('payments.amount')}
              <input
                className="ms-input"
                type="number"
                step="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                required
              />
            </label>
            <label className="ms-field">
              {t('payments.date')}
              <input
                className="ms-input"
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                required
              />
            </label>
          </div>
          <label className="ms-field">
            {t('payments.method')}
            <select
              className="ms-input"
              value={method}
              onChange={(e) => setMethod(e.target.value as PaymentMethod)}
            >
              {MANUAL_METHODS.map((m) => (
                <option key={m} value={m}>
                  {t(`payments.methodName.${m}`)}
                </option>
              ))}
            </select>
          </label>
          <button
            type="submit"
            className="ms-btn ms-btn--primary ms-btn--l ms-btn--block"
            disabled={registerPayment.isPending}
          >
            {t('payments.registerPayment')}
          </button>
          <ErrorText error={registerPayment.error} />
          {registerPayment.isSuccess && !amount && (
            <p
              role="status"
              className="ms-alert ms-alert--success"
              style={{ margin: 0, alignItems: 'center' }}
            >
              <Icon name="check" size={18} />
              <span>{t('payments.saved')}</span>
            </p>
          )}
        </form>
      </div>
    </AppShell>
  )
}
