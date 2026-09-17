import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'

import { type Role, useAuth } from './AuthProvider'

export function RequireRole({ roles, children }: { roles: Role[]; children: ReactNode }) {
  const { user, isLoading } = useAuth()

  if (isLoading) return null
  if (!user) return <Navigate to="/login" replace />
  if (!roles.includes(user.role)) return <Navigate to="/" replace />

  return <>{children}</>
}
