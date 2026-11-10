import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { Dialog, DialogActions } from '../../components/Dialog'
import { ErrorText } from '../../components/QueryState'
import { localDateISO } from '../../lib/dates'
import { useCreatePackage } from './api/packages'

/** Sell a package of lessons to a student. The price is what was agreed, typed by the teacher. */
export function PackageFormDialog({
  studentId,
  studentName,
  onClose,
}: {
  studentId: number
  studentName: string
  onClose: () => void
}) {
  const { t } = useTranslation()
  const [total, setTotal] = useState('10')
  const [price, setPrice] = useState('')
  // Local calendar date: after midnight in Italy the UTC date is still yesterday.
  const [purchaseDate, setPurchaseDate] = useState(() => localDateISO())
  const [expiryDate, setExpiryDate] = useState('')
  const create = useCreatePackage()

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    create.mutate(
      {
        student: studentId,
        total_lessons: Number(total),
        price: price.replace(',', '.'),
        purchase_date: purchaseDate,
        expiry_date: expiryDate || null,
      },
      { onSuccess: onClose },
    )
  }

  return (
    <Dialog title={t('package.new')} subtitle={studentName} onClose={onClose}>
      <form className="ms-form" onSubmit={handleSubmit}>
        <div className="ms-form__grid">
          <label className="ms-field">
            {t('package.lessons')}
            <input
              className="ms-input"
              type="number"
              min={1}
              max={999}
              value={total}
              onChange={(e) => setTotal(e.target.value)}
              required
            />
          </label>
          <label className="ms-field">
            {t('package.price')}
            <input
              className="ms-input"
              type="text"
              inputMode="decimal"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              required
            />
          </label>
        </div>
        <div className="ms-form__grid">
          <label className="ms-field">
            {t('package.purchaseDate')}
            <input
              className="ms-input"
              type="date"
              value={purchaseDate}
              onChange={(e) => setPurchaseDate(e.target.value)}
              required
            />
          </label>
          <label className="ms-field">
            {t('package.expiryDate')}
            <input
              className="ms-input"
              type="date"
              value={expiryDate}
              min={purchaseDate}
              onChange={(e) => setExpiryDate(e.target.value)}
            />
          </label>
        </div>
        <ErrorText error={create.error} />
        <DialogActions>
          <button type="button" className="ms-btn ms-btn--secondary" onClick={onClose}>
            {t('lesson.cancel')}
          </button>
          <button type="submit" className="ms-btn ms-btn--primary" disabled={create.isPending}>
            {t('common.save')}
          </button>
        </DialogActions>
      </form>
    </Dialog>
  )
}
