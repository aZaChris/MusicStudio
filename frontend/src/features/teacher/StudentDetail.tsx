import { useTranslation } from 'react-i18next'
import { useParams } from 'react-router-dom'

import { QueryState } from '../../components/QueryState'
import { Sidebar } from '../../components/Sidebar'
import { formatDateTime } from '../../lib/dates'
import { useStudent, useStudentLessons } from './api/students'

export function StudentDetail() {
  const { t, i18n } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const studentId = Number(id)
  const student = useStudent(studentId)
  const lessons = useStudentLessons(studentId)
  const pkg = student.data?.active_package

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar />
      <div style={{ flex: 1, padding: '36px 44px', maxWidth: 1280 }}>
        {/* A student that is not visible (404) shows a clear message, not an empty page. */}
        <QueryState query={student}>
          <h1 style={{ fontFamily: 'var(--ms-font-heading)', fontSize: 22, fontWeight: 600 }}>
            {student.data?.full_name}
          </h1>
          <p style={{ color: 'var(--ms-text-muted)' }}>{student.data?.instrument}</p>

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
            {pkg ? (
              <div>
                {pkg.lessons_remaining}/{pkg.total_lessons} · {t(`package.statusName.${pkg.status}`)}
              </div>
            ) : (
              <div style={{ color: 'var(--ms-text-muted)' }}>{t('roster.noPackage')}</div>
            )}
          </div>

          <h2 style={{ fontSize: 16, fontFamily: 'var(--ms-font-heading)' }}>{t('student.lessons')}</h2>
          <QueryState
            query={lessons}
            isEmpty={(lessons.data ?? []).length === 0}
            emptyText={t('student.noLessons')}
          >
            <ul style={{ display: 'flex', flexDirection: 'column', gap: 8, listStyle: 'none', padding: 0 }}>
              {lessons.data?.map((lesson) => (
                <li
                  key={lesson.id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    gap: 12,
                    padding: '8px 12px',
                    border: '1px solid var(--ms-border)',
                    borderRadius: 8,
                  }}
                >
                  <span>{formatDateTime(lesson.start_time, i18n.language)}</span>
                  <span>{t(`lesson.statusName.${lesson.status}`)}</span>
                  {lesson.notes && <span style={{ color: 'var(--ms-text-muted)' }}>{lesson.notes}</span>}
                </li>
              ))}
            </ul>
          </QueryState>
        </QueryState>
      </div>
    </div>
  )
}
