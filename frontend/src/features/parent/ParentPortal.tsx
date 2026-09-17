import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { useAuth } from '../../auth/AuthProvider'
import { useTheme } from '../../theme/ThemeProvider'
import { useStudentLessons, useStudents } from '../teacher/api/students'
import { usePayments } from '../teacher/api/payments'

function capitalize(s: string) {
  return s
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join('')
}

export function ParentPortal() {
  const { t, i18n } = useTranslation()
  const { logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const { data: students } = useStudents()
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const activeId = selectedId ?? students?.results[0]?.id ?? 0
  const { data: lessons } = useStudentLessons(activeId)
  const { data: payments } = usePayments()

  const dateFormatter = new Intl.DateTimeFormat(i18n.language, { dateStyle: 'medium', timeStyle: 'short' })
  const toggleLanguage = () => i18n.changeLanguage(i18n.language.startsWith('it') ? 'en' : 'it')

  if (students && students.results.length === 0) {
    return <p style={{ padding: 36 }}>{t('parent.noStudents')}</p>
  }

  const studentPayments = payments?.results.filter((p) => p.student === activeId) ?? []

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '36px 24px', display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ fontFamily: 'var(--ms-font-heading)', fontSize: 22, margin: 0 }}>
          {t('parent.portalTitle')}
        </h1>
        <div style={{ display: 'flex', gap: 8 }}>
          <button type="button" onClick={toggleTheme} title={t('theme.toggle')} aria-label={t('theme.toggle')}>
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

      {students && students.results.length > 1 && (
        <div style={{ display: 'flex', gap: 8 }}>
          {students.results.map((s) => (
            <button
              key={s.id}
              type="button"
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
        <h2 style={{ fontSize: 16, fontFamily: 'var(--ms-font-heading)' }}>
          {t('parent.upcomingLessons')} / {t('parent.attendance')}
        </h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {lessons?.map((lesson) => (
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
              <span>{dateFormatter.format(new Date(lesson.start_time))}</span>
              <span>{t(`lesson.status${capitalize(lesson.status)}`)}</span>
              {lesson.notes && <span style={{ color: 'var(--ms-text-muted)' }}>{lesson.notes}</span>}
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 style={{ fontSize: 16, fontFamily: 'var(--ms-font-heading)' }}>{t('parent.paymentStatus')}</h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {studentPayments.map((p) => (
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
              <span>{p.date}</span>
              <span>{p.amount}</span>
              <span>{t(`payments.status${capitalize(p.status)}`)}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
