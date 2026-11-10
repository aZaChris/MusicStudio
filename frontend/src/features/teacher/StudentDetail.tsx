import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'

import { AppShell } from '../../components/AppShell'
import { QueryState } from '../../components/QueryState'
import { Avatar, Beats, Icon, StatusChip } from '../../components/ui'
import { lessonTone, packageTone } from '../../components/tones'
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
    <AppShell>
      <Link to="/students" className="back-link">
        <Icon name="back" size={18} />
        {t('nav.students')}
      </Link>

      {/* A student that is not visible (404) shows a clear message, not an empty page. */}
      <QueryState query={student}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 18, alignItems: 'center' }}>
          <Avatar name={student.data?.full_name ?? ''} size="l" />
          <div className="page-head__text" style={{ flex: '1 1 260px' }}>
            <h1 className="page-title">{student.data?.full_name}</h1>
            <span className="page-eyebrow" style={{ fontSize: 16 }}>
              {student.data?.instrument}
            </span>
          </div>
        </div>

        <div className="two-col">
          <section className="panel">
            <div className="row-between">
              <h2 className="section-title">{t('roster.package')}</h2>
              {pkg && (
                <StatusChip tone={packageTone(pkg.status)}>
                  {t(`package.statusName.${pkg.status}`)}
                </StatusChip>
              )}
            </div>
            {pkg ? (
              <>
                <Beats size="l" total={pkg.total_lessons} used={pkg.total_lessons - pkg.lessons_remaining} />
                <span className="number-hero">
                  {t('roster.remainingCount', { count: pkg.lessons_remaining })}
                </span>
                <span className="muted" style={{ fontSize: 14 }}>
                  {pkg.lessons_remaining}/{pkg.total_lessons} · {t(`package.statusName.${pkg.status}`)}
                </span>
              </>
            ) : (
              <span className="muted" style={{ fontSize: 14 }}>
                {t('roster.noPackage')}
              </span>
            )}
          </section>

          <section className="panel" style={{ gap: 6 }}>
            <h2 className="section-title" style={{ marginBottom: 6 }}>
              {t('student.lessons')}
            </h2>
            <QueryState
              query={lessons}
              isEmpty={(lessons.data ?? []).length === 0}
              emptyText={t('student.noLessons')}
            >
              {lessons.data?.map((lesson) => (
                <div key={lesson.id} className="list-line">
                  <div className="list-line__main">
                    <span style={{ fontSize: 15, fontWeight: 700 }}>
                      {formatDateTime(lesson.start_time, i18n.language)}
                    </span>
                    {lesson.notes && <span className="muted">{lesson.notes}</span>}
                  </div>
                  <StatusChip tone={lessonTone(lesson.status)}>
                    {t(`lesson.statusName.${lesson.status}`)}
                  </StatusChip>
                </div>
              ))}
            </QueryState>
          </section>
        </div>
      </QueryState>
    </AppShell>
  )
}
