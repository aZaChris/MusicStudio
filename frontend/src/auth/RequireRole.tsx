import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate } from 'react-router-dom'

import type { Role } from '../api/types'
import { useAuth } from './useAuth'

/** UX routing only: the API enforces permissions on every request (constitution I). */
export function RequireRole({ roles, children }: { roles: Role[]; children: ReactNode }) {
  const { t } = useTranslation()
  const { user, status, retry } = useAuth()

  if (status === 'loading')
    return (
      <p aria-busy="true" className="muted" style={{ padding: 32 }}>
        {t('common.loading')}
      </p>
    )
  if (status === 'unreachable') {
    // A session is stored but cannot be confirmed: do not guess the role, do not sign out.
    return (
      <div role="alert" className="ms-alert ms-alert--warning" style={{ margin: 32, alignItems: 'center' }}>
        <span style={{ flex: 1 }}>{t('auth.unreachable')}</span>
        <button type="button" className="ms-btn ms-btn--secondary" onClick={retry}>
          {t('common.retry')}
        </button>
      </div>
    )
  }
  if (!user) return <Navigate to="/login" replace />
  if (!roles.includes(user.role)) return <Navigate to="/" replace />
  return <>{children}</>
}
