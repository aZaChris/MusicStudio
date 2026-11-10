import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { useAuth } from '../../auth/useAuth'
import { QueryState } from '../../components/QueryState'
import { formatDateTime, formatDay } from '../../lib/dates'
import { useTheme } from '../../theme/useTheme'
import { useStudentLessons, useStudents } from '../teacher/api/students'
import { usePayments } from '../teacher/api/payments'

export function ParentPortal() {
  const { t, i18n } = useTranslation()
  const { logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const studentsQuery = useStudents()
  const students = studentsQuery.data ?? []
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const activeId = selectedId ?? students[0]?.id ?? 0
  const lessons = useStudentLessons(activeId)
  const payments = usePayments(activeId) // filtered by the server: ?student=<id>

  const toggleLanguage = () => i18n.changeLanguage(i18n.language.startsWith('it') ? 'en' : 'it')

  return (
    <div
      style={{
        maxWidth: 900,
        margin: '0 auto',
        padding: '36px 24px',
        display: 'flex',
        flexDirection: 'column',
        gap: 24,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ fontFamily: 'var(--ms-font-heading)', fontSize: 22, margin: 0 }}>
          {t('parent.portalTitle')}
        </h1>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            type="button"
            onClick={toggleTheme}
            title={t('theme.toggle')}
            aria-label={t('theme.toggle')}
          >
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>
          <button
            type="button"
            onClick={toggleLanguage}
            aria-label={i18n.language.startsWith('it') ? 'Switch to English' : 'Passa all’italiano'}
          >
            {i18n.language.startsWith('it') ? 'EN' : 'IT'}
          </button>
          <button type="button" onClick={logout}>
            {t('auth.logout')}
          </button>
        </div>
      </div>

      <QueryState query={studentsQuery} isEmpty={students.length === 0} emptyText={t('parent.noStudents')}>
        {students.length > 1 && (
          <div role="tablist" style={{ display: 'flex', gap: 8 }}>
            {students.map((s) => (
              <button
                key={s.id}
                type="button"
                role="tab"
                aria-selected={activeId === s.id}
                onClick={() => setSelectedId(s.id)}
                style={{
                  padding: '6px 14px',
                  borderRadius: 999,
                  border: '1px solid var(--ms-border)',
                  background: activeId === s.id ? 'var(--ms-accent)' : 'var(--ms-surface)',
                  color: activeId === s.id ? 'white' : 'inherit',
                }}
              >
                {s.full_name}
              </button>
            ))}
          </div>
        )}

        <section>
          <h2 style={{ fontSize: 16, fontFamily: 'var(--ms-font-heading)' }}>{t('parent.lessons')}</h2>
          <QueryState
            query={lessons}
            isEmpty={(lessons.data ?? []).length === 0}
            emptyText={t('student.noLessons')}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {lessons.data?.map((lesson) => (
                <div
                  key={lesson.id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    padding: '10px 14px',
                    border: '1px solid var(--ms-border)',
                    borderRadius: 'var(--ms-radius-sm)',
                  }}
                >
                  <span>{formatDateTime(lesson.start_time, i18n.language)}</span>
                  <span>{t(`lesson.statusName.${lesson.status}`)}</span>
                  {lesson.notes && <span style={{ color: 'var(--ms-text-muted)' }}>{lesson.notes}</span>}
                </div>
              ))}
            </div>
          </QueryState>
        </section>

        <section>
          <h2 style={{ fontSize: 16, fontFamily: 'var(--ms-font-heading)' }}>{t('parent.payments')}</h2>
          <QueryState
            query={payments}
            isEmpty={(payments.data ?? []).length === 0}
            emptyText={t('payments.empty')}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {payments.data?.map((p) => (
                <div
                  key={p.id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    padding: '10px 14px',
                    border: '1px solid var(--ms-border)',
                    borderRadius: 'var(--ms-radius-sm)',
                  }}
                >
                  <span>{formatDay(p.date, i18n.language)}</span>
                  <span>€ {p.amount}</span>
                  <span>{p.status ? t(`payments.statusName.${p.status}`) : '—'}</span>
                </div>
              ))}
            </div>
          </QueryState>
        </section>
      </QueryState>
    </div>
  )
}
