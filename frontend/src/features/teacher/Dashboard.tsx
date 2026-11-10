import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import type { Lesson } from '../../api/types'
import { QueryState } from '../../components/QueryState'
import { Sidebar } from '../../components/Sidebar'
import { useAuth } from '../../auth/useAuth'
import { useDashboard } from './api/lessons'
import { LessonCompleteModal } from './LessonCompleteModal'

function groupByDay(lessons: Lesson[]): Record<number, Lesson[]> {
  const byDay: Record<number, Lesson[]> = { 0: [], 1: [], 2: [], 3: [], 4: [], 5: [], 6: [] }
  for (const lesson of lessons) {
    const day = new Date(lesson.start_time).getDay()
    byDay[day].push(lesson)
  }
  return byDay
}

const DAY_ORDER = [1, 2, 3, 4, 5, 6, 0] // Monday-first

export function Dashboard() {
  const { t, i18n } = useTranslation()
  const { user } = useAuth()
  const dashboard = useDashboard()
  const { data } = dashboard
  const [activeLesson, setActiveLesson] = useState<Lesson | null>(null)

  const dayFormatter = new Intl.DateTimeFormat(i18n.language, { weekday: 'short' })
  const timeFormatter = new Intl.DateTimeFormat(i18n.language, {
    hour: '2-digit',
    minute: '2-digit',
  })

  const byDay = data ? groupByDay(data.week) : null

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar />
      <div
        style={{
          flex: 1,
          padding: '36px 44px',
          maxWidth: 1280,
          display: 'flex',
          flexDirection: 'column',
          gap: 28,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontFamily: 'var(--ms-font-heading)', fontWeight: 600, fontSize: 26 }}>
              {t('dashboard.greeting', { name: user?.email.split('@')[0] ?? '' })}
            </div>
          </div>
          {data && (
            <div style={{ display: 'flex', gap: 28 }}>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontFamily: 'var(--ms-font-heading)', fontWeight: 700, fontSize: 22 }}>
                  {data.active_students_count}
                </div>
                <div style={{ fontSize: 12.5, color: 'var(--ms-text-muted)' }}>
                  {t('dashboard.activeStudents')}
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div
                  style={{
                    fontFamily: 'var(--ms-font-heading)',
                    fontWeight: 700,
                    fontSize: 22,
                    color: 'var(--ms-danger-text)',
                  }}
                >
                  {data.pending_payments_count}
                </div>
                <div style={{ fontSize: 12.5, color: 'var(--ms-text-muted)' }}>
                  {t('dashboard.pendingPayments')}
                </div>
              </div>
            </div>
          )}
        </div>

        <QueryState query={dashboard}>
          {byDay && (
            <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1fr', gap: 24, alignItems: 'start' }}>
              <div
                style={{
                  background: 'var(--ms-surface)',
                  borderRadius: 'var(--ms-radius-lg)',
                  border: '1px solid var(--ms-border)',
                  padding: 20,
                  overflowX: 'auto',
                }}
              >
                <div
                  style={{
                    fontFamily: 'var(--ms-font-heading)',
                    fontWeight: 600,
                    fontSize: 16,
                    marginBottom: 14,
                  }}
                >
                  {t('dashboard.thisWeek')}
                </div>
                <div
                  style={{ display: 'grid', gridTemplateColumns: 'repeat(7, minmax(120px, 1fr))', gap: 8 }}
                >
                  {DAY_ORDER.map((day) => (
                    <div key={day}>
                      <div
                        style={{
                          textAlign: 'center',
                          fontSize: 12,
                          fontWeight: 800,
                          color: 'var(--ms-text-muted)',
                          marginBottom: 6,
                        }}
                      >
                        {dayFormatter.format(new Date(2024, 0, day === 0 ? 7 : day))}
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                        {byDay[day].map((lesson) => (
                          <button
                            key={lesson.id}
                            type="button"
                            disabled={lesson.status !== 'scheduled'}
                            aria-label={`${lesson.student_name}, ${timeFormatter.format(new Date(lesson.start_time))}`}
                            onClick={() => setActiveLesson(lesson)}
                            style={{
                              textAlign: 'left',
                              fontSize: 12,
                              padding: '6px 8px',
                              borderRadius: 8,
                              border: '1px solid var(--ms-border)',
                              background:
                                lesson.status === 'completed'
                                  ? 'var(--ms-success-bg)'
                                  : 'var(--ms-surface-muted)',
                              color: lesson.status === 'completed' ? 'var(--ms-success-text)' : 'inherit',
                            }}
                          >
                            <div style={{ fontWeight: 700 }}>
                              {timeFormatter.format(new Date(lesson.start_time))}
                            </div>
                            <div>{lesson.student_name}</div>
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div
                  style={{
                    background: 'var(--ms-surface)',
                    borderRadius: 'var(--ms-radius-lg)',
                    border: '1px solid var(--ms-border)',
                    padding: 20,
                  }}
                >
                  <div
                    style={{
                      fontFamily: 'var(--ms-font-heading)',
                      fontWeight: 600,
                      fontSize: 16,
                      marginBottom: 12,
                    }}
                  >
                    {t('dashboard.upcoming')}
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {data?.upcoming.length === 0 && (
                      <span style={{ color: 'var(--ms-text-muted)' }}>{t('dashboard.noUpcoming')}</span>
                    )}
                    {data?.upcoming.map((lesson) => (
                      <div
                        key={lesson.id}
                        style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13.5 }}
                      >
                        <span>{lesson.student_name}</span>
                        <span style={{ color: 'var(--ms-text-muted)' }}>
                          {timeFormatter.format(new Date(lesson.start_time))}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {data && data.low_package_students.length > 0 && (
                  <div
                    style={{
                      background: 'var(--ms-warning-bg)',
                      color: 'var(--ms-warning-text)',
                      borderRadius: 'var(--ms-radius-lg)',
                      padding: 16,
                      fontSize: 13.5,
                    }}
                  >
                    {data.low_package_students.map((s) => s.full_name).join(', ')} — {t('roster.lowPackage')}
                  </div>
                )}
              </div>
            </div>
          )}
        </QueryState>
      </div>

      {activeLesson && (
        <LessonCompleteModal
          lessonId={activeLesson.id}
          studentName={activeLesson.student_name}
          onClose={() => setActiveLesson(null)}
        />
      )}
    </div>
  )
}
