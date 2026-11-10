import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { useAuth } from '../../auth/useAuth'
import { QueryState } from '../../components/QueryState'
import { Beats, Icon, Logo, StatusChip } from '../../components/ui'
import { lessonTone, paymentTone } from '../../components/tones'
import { formatDateTime, formatDay } from '../../lib/dates'
import { useTheme } from '../../theme/useTheme'
import { useStudentLessons, useStudents } from '../teacher/api/students'
import { usePayments } from '../teacher/api/payments'

export function ParentPortal() {
  const { t, i18n } = useTranslation()
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const studentsQuery = useStudents()
  const students = studentsQuery.data ?? []
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const activeId = selectedId ?? students[0]?.id ?? 0
  const active = students.find((s) => s.id === activeId)
  const pkg = active?.active_package
  const lessons = useStudentLessons(activeId)
  const payments = usePayments(activeId) // filtered by the server: ?student=<id>

  const isItalian = i18n.language.startsWith('it')
  const toggleLanguage = () => i18n.changeLanguage(isItalian ? 'en' : 'it')
  const money = new Intl.NumberFormat(isItalian ? 'it-IT' : 'en-GB', { style: 'currency', currency: 'EUR' })

  // The earliest lesson still to come.
  const now = new Date()
  const next = (lessons.data ?? [])
    .filter((l) => l.status === 'scheduled' && new Date(l.start_time) >= now)
    .sort((a, b) => +new Date(a.start_time) - +new Date(b.start_time))[0]

  return (
    <>
      <header className="portal-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Logo size={40} />
          <span className="ms-role-tag">{t('parent.role')}</span>
        </div>
        <div className="portal-header__tools">
          <span className="muted" style={{ color: 'var(--plum-soft)', fontSize: 14 }}>
            {user?.email}
          </span>
          <button
            type="button"
            className="ms-btn ms-btn--on-plum"
            onClick={toggleTheme}
            title={t('theme.toggle')}
            aria-label={t('theme.toggle')}
          >
            {theme === 'dark' ? t('theme.light') : t('theme.dark')}
          </button>
          <button
            type="button"
            className="ms-btn ms-btn--on-plum"
            onClick={toggleLanguage}
            aria-label={isItalian ? 'Switch to English' : 'Passa all’italiano'}
          >
            {isItalian ? 'EN' : 'IT'}
          </button>
          <button type="button" className="ms-btn ms-btn--on-plum" onClick={logout}>
            {t('auth.logout')}
          </button>
        </div>
      </header>

      <main className="portal-main">
        <div className="page-head">
          <h1 className="page-title">{t('parent.portalTitle')}</h1>
          {students.length > 1 && (
            <div role="tablist" aria-label={t('parent.children')} className="ms-filters ms-filters--accent">
              {students.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  role="tab"
                  className="ms-filter"
                  aria-selected={activeId === s.id}
                  onClick={() => setSelectedId(s.id)}
                >
                  {s.full_name}
                </button>
              ))}
            </div>
          )}
        </div>

        <QueryState query={studentsQuery} isEmpty={students.length === 0} emptyText={t('parent.noStudents')}>
          <div className="two-col">
            <section className="panel panel--plum">
              <div className="row-between" style={{ alignItems: 'flex-start' }}>
                <div className="list-line__main" style={{ gap: 4 }}>
                  <span className="ms-label">{t('parent.nextLesson')}</span>
                  <span style={{ fontFamily: 'var(--font-display)', fontSize: 28, fontWeight: 800 }}>
                    {next ? formatDateTime(next.start_time, i18n.language) : t('parent.noNextLesson')}
                  </span>
                  <span style={{ color: 'var(--plum-soft)', fontWeight: 600 }}>{active?.instrument}</span>
                </div>
                <span style={{ color: 'var(--orange)' }}>
                  <Icon name="note" size={40} />
                </span>
              </div>
              {pkg && (
                <>
                  <Beats onPlum total={pkg.total_lessons} used={pkg.total_lessons - pkg.lessons_remaining} />
                  <span style={{ fontWeight: 700 }}>
                    {t('parent.remaining', { count: pkg.lessons_remaining })}
                  </span>
                </>
              )}
            </section>

            <section className="panel" style={{ gap: 6 }}>
              <h2 className="section-title" style={{ marginBottom: 6 }}>
                {t('parent.lessons')}
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
                    <StatusChip tone={lessonTone(lesson.status)} small>
                      {t(`lesson.statusName.${lesson.status}`)}
                    </StatusChip>
                  </div>
                ))}
              </QueryState>
            </section>

            <section className="panel" style={{ gap: 6 }}>
              <h2 className="section-title" style={{ marginBottom: 6 }}>
                {t('parent.payments')}
              </h2>
              <QueryState
                query={payments}
                isEmpty={(payments.data ?? []).length === 0}
                emptyText={t('payments.empty')}
              >
                {payments.data?.map((p) => (
                  <div key={p.id} className="list-line">
                    <div className="list-line__main">
                      <span style={{ fontSize: 15, fontWeight: 700 }}>
                        {formatDay(p.date, i18n.language)}
                      </span>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
                      <span className="ms-amount">{money.format(Number(p.amount))}</span>
                      {p.status ? (
                        <StatusChip tone={paymentTone(p.status)} small>
                          {t(`payments.statusName.${p.status}`)}
                        </StatusChip>
                      ) : (
                        '—'
                      )}
                    </div>
                  </div>
                ))}
              </QueryState>
              <p className="muted" style={{ margin: '8px 0 0', fontWeight: 500 }}>
                {t('parent.paymentsHint')}
              </p>
            </section>
          </div>
        </QueryState>
      </main>
    </>
  )
}
