import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

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
  const noteRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    noteRef.current?.focus()
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  // On failure the dialog stays open with the server's reason (e.g. 409 already completed).
  const handleComplete = () => completeLesson.mutate({ id: lessonId, note }, { onSuccess: onClose })

  return (
    <div className="ms-modal" onClick={onClose}>
      <div
        className="ms-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="lesson-complete-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="ms-stack" style={{ gap: 4 }}>
          <h2 id="lesson-complete-title" className="ms-overlay-title">
            {t('lesson.markComplete')}
          </h2>
          <span className="ms-overlay-sub">{studentName}</span>
        </div>
        <label className="ms-field">
          {t('lesson.note')}
          <textarea
            ref={noteRef}
            className="ms-input"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={4}
          />
        </label>
        <ErrorText error={completeLesson.error} />
        <div className="row-between" style={{ justifyContent: 'flex-end', flexWrap: 'wrap' }}>
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
        </div>
      </div>
    </div>
  )
}
