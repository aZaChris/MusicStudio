import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'

import { AppShell } from '../../components/AppShell'
import { QueryState } from '../../components/QueryState'
import { Avatar, Beats, Icon, StatusChip } from '../../components/ui'
import { lessonTone, packageTone } from '../../components/tones'
import { formatDateTime, formatDay } from '../../lib/dates'
import { useCancelLesson } from './api/lessons'
import { useStudent, useStudentLessons } from './api/students'
import { InviteDialog } from './InviteDialog'
import { LessonFormDialog } from './LessonFormDialog'
import { PackageFormDialog } from './PackageFormDialog'
import { StudentFormDialog } from './StudentFormDialog'

export function StudentDetail() {
  const { t, i18n } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const studentId = Number(id)
  const student = useStudent(studentId)
  const lessons = useStudentLessons(studentId)
  const pkg = student.data?.active_package
  const cancelLesson = useCancelLesson()
  const [dialog, setDialog] = useState<
    'edit' | 'package' | 'lesson' | 'inviteParent' | 'inviteStudent' | null
  >(null)

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
          <div className="page-actions">
            <button type="button" className="ms-btn ms-btn--secondary" onClick={() => setDialog('edit')}>
              {t('student.edit')}
            </button>
            <button
              type="button"
              className="ms-btn ms-btn--secondary"
              onClick={() => setDialog('inviteParent')}
            >
              {t('invite.parentButton')}
            </button>
            {student.data?.is_adult && !student.data.has_account && (
              <button
                type="button"
                className="ms-btn ms-btn--secondary"
                onClick={() => setDialog('inviteStudent')}
              >
                {t('invite.studentButton')}
              </button>
            )}
            <button type="button" className="ms-btn ms-btn--secondary" onClick={() => setDialog('package')}>
              {t('package.new')}
            </button>
            <button type="button" className="ms-btn ms-btn--primary" onClick={() => setDialog('lesson')}>
              {t('lesson.schedule')}
            </button>
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
                <span className="muted" style={{ fontSize: 14, fontWeight: 500 }}>
                  {t('package.boughtOn', { date: formatDay(pkg.purchase_date, i18n.language) })}
                  {pkg.expiry_date
                    ? ` · ${t('package.expiresOn', { date: formatDay(pkg.expiry_date, i18n.language) })}`
                    : ''}
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
                  <div className="page-actions" style={{ alignItems: 'center' }}>
                    {lesson.status === 'scheduled' && (
                      <>
                        <button
                          type="button"
                          className="ms-btn ms-btn--ghost ms-btn--s"
                          disabled={cancelLesson.isPending}
                          onClick={() => cancelLesson.mutate({ id: lesson.id, status: 'cancelled' })}
                        >
                          {t('lesson.cancelLesson')}
                        </button>
                        <button
                          type="button"
                          className="ms-btn ms-btn--ghost ms-btn--s"
                          disabled={cancelLesson.isPending}
                          onClick={() => cancelLesson.mutate({ id: lesson.id, status: 'no_show' })}
                        >
                          {t('lesson.noShow')}
                        </button>
                      </>
                    )}
                    <StatusChip tone={lessonTone(lesson.status)}>
                      {t(`lesson.statusName.${lesson.status}`)}
                    </StatusChip>
                  </div>
                </div>
              ))}
            </QueryState>
          </section>
        </div>
      </QueryState>

      {(dialog === 'inviteParent' || dialog === 'inviteStudent') && (
        <InviteDialog
          studentId={studentId}
          role={dialog === 'inviteParent' ? 'parent' : 'student'}
          onClose={() => setDialog(null)}
        />
      )}
      {dialog === 'edit' && student.data && (
        <StudentFormDialog student={student.data} onClose={() => setDialog(null)} />
      )}
      {dialog === 'package' && student.data && (
        <PackageFormDialog
          studentId={student.data.id}
          studentName={student.data.full_name}
          onClose={() => setDialog(null)}
        />
      )}
      {dialog === 'lesson' && student.data && (
        <LessonFormDialog
          studentId={student.data.id}
          studentName={student.data.full_name}
          onClose={() => setDialog(null)}
        />
      )}
    </AppShell>
  )
}
