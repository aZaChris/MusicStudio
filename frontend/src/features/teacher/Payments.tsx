import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import type { Payment, PaymentMethod } from '../../api/types'
import { AppShell } from '../../components/AppShell'
import { ErrorText, QueryState } from '../../components/QueryState'
import { Icon, StatusChip } from '../../components/ui'
import { paymentTone } from '../../components/tones'
import { formatDay, localDateISO } from '../../lib/dates'
import { monthPeriod, type Period } from '../../lib/period'
import { useIssueReceipt, usePayments, useRegisterPayment } from './api/payments'
import { useStudents } from './api/students'
import { RegisterPanel } from './RegisterPanel'
import { ReversePaymentDialog } from './ReversePaymentDialog'

// Online card payments come from Stripe webhooks, never from this form.
const MANUAL_METHODS: PaymentMethod[] = ['cash', 'bank_transfer', 'manual_entry']

type Filter = 'all' | 'pending' | 'paid'
const FILTERS: Filter[] = ['all', 'pending', 'paid']

// Money still to collect: only pending and overdue entries. A reversal row is history.
const isToCollect = (p: Payment) => p.status === 'pending' || p.status === 'overdue'
// A paid entry that was reversed reads "reversed"; the server keeps its stored status as paid.
const displayStatus = (p: Payment) => (p.reversed ? 'reversed' : p.status)

export function Payments() {
  const { t, i18n } = useTranslation()
  // The register shows one period at a time (default: this month); the server filters.
  const [period, setPeriod] = useState<Period>(() => monthPeriod(localDateISO().slice(0, 7)))
  const payments = usePayments(undefined, period)
  const { data: students } = useStudents()
  const registerPayment = useRegisterPayment()
  const issueReceipt = useIssueReceipt()

  const [studentId, setStudentId] = useState('')
  const [amount, setAmount] = useState('')
  // Local calendar date: after midnight in Italy the UTC date is still yesterday.
  const [date, setDate] = useState(() => localDateISO())
  const [method, setMethod] = useState<PaymentMethod>('cash')
  const [filter, setFilter] = useState<Filter>('all')
  const [toReverse, setToReverse] = useState<Payment | null>(null)

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!studentId || !amount) return
    registerPayment.mutate(
      { student: Number(studentId), amount, date, method, status: 'paid' },
      { onSuccess: () => setAmount('') }, // on failure the form keeps what was typed
    )
  }

  const all = payments.data ?? []
  const toCollect = all.filter(isToCollect).length
  const shown = all.filter(
    (p) => filter === 'all' || (filter === 'paid' ? p.status === 'paid' : isToCollect(p)),
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

      <RegisterPanel period={period} onChange={setPeriod} money={money} />

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
                    <th scope="col" aria-label={t('payments.reverse.action')} />
                  </tr>
                </thead>
                <tbody>
                  {shown.map((payment) => (
                    <tr key={payment.id}>
                      <td>
                        {payment.student_name}
                        {payment.status === 'reversal' && (
                          <small style={{ display: 'block' }}>
                            {payment.cause !== 'manual' && `${t(`payments.cause.${payment.cause}`)} · `}
                            {t('payments.reverse.of', { id: payment.reversal_of })}
                            {payment.reason &&
                              ` — ${t('payments.reverse.reasonLabel', { reason: payment.reason })}`}
                          </small>
                        )}
                      </td>
                      <td>{formatDay(payment.date, i18n.language)}</td>
                      <td>{payment.method ? t(`payments.methodName.${payment.method}`) : '—'}</td>
                      <td className="num">{money.format(Number(payment.amount))}</td>
                      <td style={{ textAlign: 'right' }}>
                        {payment.status ? (
                          <StatusChip tone={paymentTone(displayStatus(payment))} small>
                            {t(`payments.statusName.${displayStatus(payment)}`)}
                          </StatusChip>
                        ) : (
                          '—'
                        )}
                        {payment.under_dispute && (
                          <small style={{ display: 'block' }}>{t('payments.underDispute')}</small>
                        )}
                        {!payment.reversed && Number(payment.reversed_amount) > 0 && (
                          <small style={{ display: 'block' }}>
                            {t('payments.partlyRefunded', {
                              amount: money.format(Number(payment.reversed_amount)),
                            })}
                          </small>
                        )}
                      </td>
                      <td>
                        {payment.status === 'paid' && (
                          <>
                            <button
                              type="button"
                              className="ms-btn ms-btn--secondary ms-btn--s"
                              disabled={issueReceipt.isPending}
                              onClick={() =>
                                issueReceipt.mutate({
                                  paymentId: payment.id,
                                  language: i18n.language.startsWith('it') ? 'it' : 'en',
                                })
                              }
                            >
                              {payment.receipt_number
                                ? t('payments.receipt.download', { number: payment.receipt_number })
                                : t('payments.receipt.action')}
                            </button>
                            {!payment.reversed && Number(payment.reversed_amount) === 0 && (
                              <button
                                type="button"
                                className="ms-btn ms-btn--secondary ms-btn--s"
                                onClick={() => setToReverse(payment)}
                              >
                                {t('payments.reverse.action')}
                              </button>
                            )}
                          </>
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
          <fieldset className="ms-fieldset">
            <legend>{t('payments.method')}</legend>
            <div className="ms-filters">
              {MANUAL_METHODS.map((m) => (
                <label key={m} className="ms-radio-pill" data-checked={method === m}>
                  <input
                    type="radio"
                    name="method"
                    value={m}
                    checked={method === m}
                    onChange={() => setMethod(m)}
                  />
                  {t(`payments.methodName.${m}`)}
                </label>
              ))}
            </div>
          </fieldset>
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
      <ErrorText error={issueReceipt.error} />
      {toReverse && (
        <ReversePaymentDialog payment={toReverse} money={money} onClose={() => setToReverse(null)} />
      )}
    </AppShell>
  )
}
