import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import type { Payment } from '../../api/types'
import { Dialog, DialogActions } from '../../components/Dialog'
import { ErrorText } from '../../components/QueryState'
import { formatDay } from '../../lib/dates'
import { useReversePayment } from './api/payments'

const MAX_REASON = 200

/** Ask why, then reverse. A card entry says clearly that no money goes back (FR-007). */
export function ReversePaymentDialog({
  payment,
  money,
  onClose,
}: {
  payment: Payment
  money: Intl.NumberFormat
  onClose: () => void
}) {
  const { t, i18n } = useTranslation()
  const [reason, setReason] = useState('')
  const reverse = useReversePayment()

  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (!reason.trim()) return
    reverse.mutate({ id: payment.id, reason: reason.trim() }, { onSuccess: onClose })
  }

  return (
    <Dialog
      title={t('payments.reverse.title')}
      subtitle={t('payments.reverse.subtitle', {
        student: payment.student_name,
        amount: money.format(Number(payment.amount)),
        date: formatDay(payment.date, i18n.language),
      })}
      onClose={onClose}
    >
      <form className="ms-form" onSubmit={submit}>
        <label className="ms-field">
          {t('payments.reverse.reason')}
          <textarea
            className="ms-input"
            value={reason}
            maxLength={MAX_REASON}
            rows={3}
            onChange={(e) => setReason(e.target.value)}
            required
          />
        </label>
        <p style={{ margin: 0 }}>{t('payments.reverse.hint')}</p>
        {payment.method === 'card' && (
          <p role="note" className="ms-alert ms-alert--warning" style={{ margin: 0 }}>
            {t('payments.reverse.cardNotice')}
          </p>
        )}
        <ErrorText error={reverse.error} />
        <DialogActions>
          <button type="button" className="ms-btn ms-btn--secondary" onClick={onClose}>
            {t('lesson.cancel')}
          </button>
          <button
            type="submit"
            className="ms-btn ms-btn--primary"
            disabled={reverse.isPending || !reason.trim()}
          >
            {t('payments.reverse.confirm')}
          </button>
        </DialogActions>
      </form>
    </Dialog>
  )
}
