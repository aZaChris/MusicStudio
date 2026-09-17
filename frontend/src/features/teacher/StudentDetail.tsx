import { useTranslation } from 'react-i18next'
import { useParams } from 'react-router-dom'

import { Sidebar } from '../../components/Sidebar'
import { useStudent, useStudentLessons } from './api/students'

export function StudentDetail() {
  const { t, i18n } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const studentId = Number(id)
  const { data: student } = useStudent(studentId)
  const { data: lessons } = useStudentLessons(studentId)

  const dateFormatter = new Intl.DateTimeFormat(i18n.language, { dateStyle: 'medium', timeStyle: 'short' })

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar />
      <div style={{ flex: 1, padding: '36px 44px', maxWidth: 1280 }}>
        {student && (
          <>
            <h1 style={{ fontFamily: 'var(--ms-font-heading)', fontSize: 22, fontWeight: 600 }}>
              {student.full_name}
            </h1>
            <p style={{ color: 'var(--ms-text-muted)' }}>{student.instrument}</p>

            {student.active_package && (
              <div
                style={{
                  background: 'var(--ms-surface)',
                  border: '1px solid var(--ms-border)',
                  borderRadius: 'var(--ms-radius-lg)',
                  padding: 16,
                  marginBottom: 24,
                  maxWidth: 320,
                }}
              >
                <div style={{ fontWeight: 700 }}>{t('roster.package')}</div>
                <div>
                  {student.active_package.lessons_remaining}/{student.active_package.total_lessons}{' '}
                  ({t(`roster.package`)}: {student.active_package.status})
                </div>
              </div>
            )}

            <h2 style={{ fontSize: 16, fontFamily: 'var(--ms-font-heading)' }}>
              {t('dashboard.upcoming')}
            </h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {lessons?.map((lesson) => (
                <div
                  key={lesson.id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    border: '1px solid var(--ms-border)',
                    borderRadius: 8,
                  }}
                >
                  <span>{dateFormatter.format(new Date(lesson.start_time))}</span>
                  <span>{t(`lesson.status${capitalize(lesson.status)}`)}</span>
                  {lesson.notes && <span style={{ color: 'var(--ms-text-muted)' }}>{lesson.notes}</span>}
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function capitalize(s: string) {
  return s
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join('')
}
