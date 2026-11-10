import { useState } from 'react'
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

  // On failure the dialog stays open with the server's reason (e.g. 409 already completed).
  const handleComplete = () => completeLesson.mutate({ id: lessonId, note }, { onSuccess: onClose })

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.3)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 10,
      }}
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="lesson-complete-title"
        onClick={(e) => e.stopPropagation()}
        style={{
          background: 'var(--ms-surface)',
          borderRadius: 'var(--ms-radius-lg)',
          padding: 24,
          width: 360,
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
        }}
      >
        <h2
          id="lesson-complete-title"
          style={{ margin: 0, fontFamily: 'var(--ms-font-heading)', fontSize: 18 }}
        >
          {studentName}
        </h2>
        <label>
          {t('lesson.note')}
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={3}
            style={{ width: '100%' }}
          />
        </label>
        <ErrorText error={completeLesson.error} />
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button type="button" onClick={onClose}>
            {t('lesson.cancel')}
          </button>
          <button type="button" onClick={handleComplete} disabled={completeLesson.isPending}>
            {t('lesson.markComplete')}
          </button>
        </div>
      </div>
    </div>
  )
}
