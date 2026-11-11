import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import type { Lesson } from '../../api/types'
import { AppDownload } from '../../components/AppDownload'
import { AppShell } from '../../components/AppShell'
import { QueryState } from '../../components/QueryState'
import { Icon, StatusChip } from '../../components/ui'
import { paymentTone } from '../../components/tones'
import { formatDay } from '../../lib/dates'
import { useAuth } from '../../auth/useAuth'
import { useDashboard } from './api/lessons'
import { usePayments } from './api/payments'
import { LessonCompleteModal } from './LessonCompleteModal'

export function Dashboard() {
  const { t, i18n } = useTranslation()
  const { user } = useAuth()
  const dashboard = useDashboard()
  const payments = usePayments()
  const { data } = dashboard
  const [activeLesson, setActiveLesson] = useState<Lesson | null>(null)

  const lng = i18n.language.startsWith('it') ? 'it-IT' : 'en-GB'
  const money = new Intl.NumberFormat(lng, { style: 'currency', currency: 'EUR' })
  // The four most recent, newest first (dates are plain YYYY-MM-DD, so they sort as text).
  const recent = [...(payments.data ?? [])].sort((x, y) => y.date.localeCompare(x.date)).slice(0, 4)
  const today = new Date()
  const todayLabel = new Intl.DateTimeFormat(lng, { weekday: 'long', day: 'numeric', month: 'long' }).format(
    today,
  )
  const dayShort = new Intl.DateTimeFormat(lng, { weekday: 'short' })
  const time = new Intl.DateTimeFormat(lng, { hour: '2-digit', minute: '2-digit' })
  const dayOf = (iso: string) => {
    const d = new Date(iso)
    return d.toDateString() === today.toDateString() ? t('dashboard.today') : dayShort.format(d)
  }

  return (
    <AppShell>
      <div className="page-head">
        <div className="page-head__text">
          <span className="page-eyebrow">{todayLabel}</span>
          <h1 className="page-title">{t('dashboard.greeting', { name: user?.email.split('@')[0] ?? '' })}</h1>
        </div>
        <Link to="/payments" className="ms-btn ms-btn--primary">
          {t('payments.registerPayment')}
        </Link>
      </div>

      <QueryState query={dashboard}>
        {data && (
          <>
            <div className="stat-grid">
              <Link to="/students" className="ms-stat ms-stat--plum">
                <span className="ms-stat__value">{data.active_students_count}</span>
                <span className="ms-stat__label">{t('dashboard.activeStudents')}</span>
              </Link>
              <Link to="/payments" className="ms-stat ms-stat--orange">
                <span className="ms-stat__value">{data.pending_payments_count}</span>
                <span className="ms-stat__label">{t('dashboard.pendingPayments')}</span>
              </Link>
              <Link to="/students" className="ms-stat ms-stat--card">
                <span className="ms-stat__value">{data.low_package_students.length}</span>
                <span className="ms-stat__label">{t('dashboard.lowPackages')}</span>
              </Link>
            </div>

            {data.low_package_students.length > 0 && (
              <div className="ms-alert ms-alert--package" style={{ alignItems: 'center' }}>
                <Icon name="alert" size={22} />
                <span>
                  {data.low_package_students.map((s) => s.full_name).join(', ')} — {t('roster.lowPackage')}
                </span>
              </div>
            )}

            <div className="two-col">
              <section className="panel">
                <h2 className="section-title">{t('dashboard.upcoming')}</h2>
                {data.upcoming.length === 0 && <p className="muted">{t('dashboard.noUpcoming')}</p>}
                {data.upcoming.map((lesson) => (
                  <div key={lesson.id} className="list-line">
                    <div className="ms-timebox">
                      <span className="ms-timebox__time">{time.format(new Date(lesson.start_time))}</span>
                      <span className="ms-timebox__day">{dayOf(lesson.start_time)}</span>
                    </div>
                    <div className="list-line__main" style={{ flex: 1 }}>
                      <span style={{ fontSize: 16, fontWeight: 700 }}>{lesson.student_name}</span>
                      <span className="muted">
                        {t('dashboard.minutes', { count: lesson.duration_minutes })}
                      </span>
                    </div>
                    <button
                      type="button"
                      className="ms-btn ms-btn--success"
                      style={{ height: 40, fontSize: 14 }}
                      disabled={lesson.status !== 'scheduled'}
                      aria-label={`${t('lesson.complete')}: ${lesson.student_name}, ${time.format(new Date(lesson.start_time))}`}
                      onClick={() => setActiveLesson(lesson)}
                    >
                      {t('lesson.complete')}
                    </button>
                  </div>
                ))}
              </section>

              <section className="panel">
                <h2 className="section-title">{t('dashboard.recentPayments')}</h2>
                <QueryState
                  query={payments}
                  isEmpty={(payments.data ?? []).length === 0}
                  emptyText={t('payments.empty')}
                >
                  <div className="ms-table-wrap">
                    <table className="ms-table">
                      <thead>
                        <tr>
                          <th scope="col">{t('roster.student')}</th>
                          <th scope="col">{t('payments.date')}</th>
                          <th scope="col" style={{ textAlign: 'right' }}>
                            {t('payments.amount')}
                          </th>
                          <th scope="col" style={{ textAlign: 'right' }}>
                            {t('payments.status')}
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {recent.map((p) => (
                          <tr key={p.id}>
                            <td>{p.student_name}</td>
                            <td>{formatDay(p.date, i18n.language)}</td>
                            <td className="num">{money.format(Number(p.amount))}</td>
                            <td style={{ textAlign: 'right' }}>
                              {p.status ? (
                                <StatusChip tone={paymentTone(p.status)} small>
                                  {t(`payments.statusName.${p.status}`)}
                                </StatusChip>
                              ) : (
                                '—'
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </QueryState>
              </section>
            </div>
          </>
        )}
      </QueryState>

      <AppDownload />

      {activeLesson && (
        <LessonCompleteModal
          lessonId={activeLesson.id}
          studentName={activeLesson.student_name}
          onClose={() => setActiveLesson(null)}
        />
      )}
    </AppShell>
  )
}
