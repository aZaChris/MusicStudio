import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import type { Student } from '../../api/types'
import { Dialog, DialogActions } from '../../components/Dialog'
import { ErrorText } from '../../components/QueryState'
import { useCreateStudent, useUpdateStudent } from './api/students'

/**
 * Add a student, or edit one (`student` given). Editing also lets the teacher archive the
 * student: the lists show active students only, nothing is deleted.
 */
export function StudentFormDialog({
  student,
  onClose,
  onSaved,
}: {
  student?: Student
  onClose: () => void
  onSaved?: (student: Student) => void
}) {
  const { t } = useTranslation()
  const [firstName, setFirstName] = useState(student?.first_name ?? '')
  const [lastName, setLastName] = useState(student?.last_name ?? '')
  const [instrument, setInstrument] = useState(student?.instrument ?? '')
  const [active, setActive] = useState(student?.is_active ?? true)
  const create = useCreateStudent()
  const update = useUpdateStudent(student?.id ?? 0)
  const mutation = student ? update : create

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    const data = {
      first_name: firstName.trim(),
      last_name: lastName.trim(),
      instrument: instrument.trim(),
      ...(student ? { is_active: active } : {}),
    }
    mutation.mutate(data, {
      onSuccess: (saved) => {
        onSaved?.(saved)
        onClose()
      },
    })
  }

  return (
    <Dialog title={student ? t('student.edit') : t('student.new')} onClose={onClose}>
      <form className="ms-form" onSubmit={handleSubmit}>
        <div className="ms-form__grid">
          <label className="ms-field">
            {t('student.firstName')}
            <input
              className="ms-input"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              maxLength={100}
              required
            />
          </label>
          <label className="ms-field">
            {t('student.lastName')}
            <input
              className="ms-input"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              maxLength={100}
              required
            />
          </label>
        </div>
        <label className="ms-field">
          {t('student.instrument')}
          <input
            className="ms-input"
            value={instrument}
            onChange={(e) => setInstrument(e.target.value)}
            maxLength={100}
            required
          />
        </label>
        {student && (
          <label className="ms-check">
            <input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} />
            {t('student.active')}
          </label>
        )}
        <ErrorText error={mutation.error} />
        <DialogActions>
          <button type="button" className="ms-btn ms-btn--secondary" onClick={onClose}>
            {t('lesson.cancel')}
          </button>
          <button type="submit" className="ms-btn ms-btn--primary" disabled={mutation.isPending}>
            {t('common.save')}
          </button>
        </DialogActions>
      </form>
    </Dialog>
  )
}
