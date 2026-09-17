import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { Sidebar } from '../../components/Sidebar'
import { useStudents } from './api/students'

export function Roster() {
  const { t } = useTranslation()
  const { data, isLoading } = useStudents()

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar />
      <div style={{ flex: 1, padding: '36px 44px', maxWidth: 1280 }}>
        <h1 style={{ fontFamily: 'var(--ms-font-heading)', fontSize: 22, fontWeight: 600 }}>
          {t('roster.title')}
        </h1>

        {isLoading && <p>…</p>}

        {data && (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ textAlign: 'left', fontSize: 12.5, color: 'var(--ms-text-muted)' }}>
                <th style={{ padding: '10px 8px' }}>{t('roster.student')}</th>
                <th style={{ padding: '10px 8px' }}>{t('roster.package')}</th>
                <th style={{ padding: '10px 8px' }}>{t('roster.remaining')}</th>
                <th style={{ padding: '10px 8px' }}>{t('roster.paymentStatus')}</th>
              </tr>
            </thead>
            <tbody>
              {data.results.map((student) => (
                <tr
                  key={student.id}
                  style={{ borderTop: '1px solid var(--ms-border)', fontSize: 14 }}
                >
                  <td style={{ padding: '10px 8px' }}>
                    <Link to={`/students/${student.id}`}>{student.full_name}</Link>
                  </td>
                  <td style={{ padding: '10px 8px' }}>
                    {student.active_package
                      ? `${student.active_package.lessons_remaining}/${student.active_package.total_lessons}`
                      : '—'}
                  </td>
                  <td style={{ padding: '10px 8px' }}>
                    {student.active_package?.is_low && (
                      <span
                        style={{
                          background: 'var(--ms-warning-bg)',
                          color: 'var(--ms-warning-text)',
                          borderRadius: 999,
                          padding: '2px 8px',
                          fontSize: 12,
                        }}
                      >
                        {t('roster.lowPackage')}
                      </span>
                    )}
                  </td>
                  <td style={{ padding: '10px 8px' }}>
                    {student.payment_status ? t(`payments.status${capitalize(student.payment_status)}`) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1)
}
