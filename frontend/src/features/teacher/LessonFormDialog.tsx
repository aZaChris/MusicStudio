import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { Dialog, DialogActions } from '../../components/Dialog'
import { ErrorText } from '../../components/QueryState'
import { localDateISO, localDateTimeToISO } from '../../lib/dates'
import { useCreateLesson } from './api/lessons'

/**
 * Schedule a lesson. The server attaches the student's active package; an overlap with another
 * lesson of the same teacher comes back as a 409 with the reason, shown in the dialog.
 */
export function LessonFormDialog({
  studentId,
  studentName,
  onClose,
}: {
  studentId: number
  studentName: string
  onClose: () => void
}) {
  const { t } = useTranslation()
  const [day, setDay] = useState(() => localDateISO())
  const [time, setTime] = useState('16:00')
  const [minutes, setMinutes] = useState('45')
  const [notes, setNotes] = useState('')
  const create = useCreateLesson()

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    create.mutate(
      {
        student: studentId,
        start_time: localDateTimeToISO(day, time),
        duration_minutes: Number(minutes),
        notes,
      },
      { onSuccess: onClose },
    )
  }

  return (
    <Dialog title={t('lesson.schedule')} subtitle={studentName} onClose={onClose}>
      <form className="ms-form" onSubmit={handleSubmit}>
        <div className="ms-form__grid">
          <label className="ms-field">
            {t('lesson.day')}
            <input
              className="ms-input"
              type="date"
              value={day}
              onChange={(e) => setDay(e.target.value)}
              required
            />
          </label>
          <label className="ms-field">
            {t('lesson.time')}
            <input
              className="ms-input"
              type="time"
              value={time}
              onChange={(e) => setTime(e.target.value)}
              required
            />
          </label>
        </div>
        <label className="ms-field">
          {t('lesson.duration')}
          <input
            className="ms-input"
            type="number"
            min={5}
            max={480}
            step={5}
            value={minutes}
            onChange={(e) => setMinutes(e.target.value)}
            required
          />
        </label>
        <label className="ms-field">
          {t('lesson.noteOptional')}
          <textarea className="ms-input" rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </label>
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
