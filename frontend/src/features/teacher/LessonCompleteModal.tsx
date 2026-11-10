import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { Dialog, DialogActions } from '../../components/Dialog'
import { ErrorText } from '../../components/QueryState'
import { useCompleteLesson } from './api/lessons'

export function LessonCompleteModal({
  lessonId,
  studentName,
  onClose,
}: {
  lessonId: number
  studentName: string
  onClose: () => void
}) {
  const { t } = useTranslation()
  const [note, setNote] = useState('')
  const completeLesson = useCompleteLesson()

  // On failure the dialog stays open with the server's reason (e.g. 409 already completed).
  const handleComplete = () => completeLesson.mutate({ id: lessonId, note }, { onSuccess: onClose })

  return (
    <Dialog title={t('lesson.markComplete')} subtitle={studentName} onClose={onClose}>
      <label className="ms-field">
        {t('lesson.note')}
        <textarea className="ms-input" value={note} onChange={(e) => setNote(e.target.value)} rows={4} />
      </label>
      <ErrorText error={completeLesson.error} />
      <DialogActions>
        <button type="button" className="ms-btn ms-btn--secondary" onClick={onClose}>
          {t('lesson.cancel')}
        </button>
        <button
          type="button"
          className="ms-btn ms-btn--primary"
          onClick={handleComplete}
          disabled={completeLesson.isPending}
        >
          {t('lesson.complete')}
        </button>
      </DialogActions>
    </Dialog>
  )
}
