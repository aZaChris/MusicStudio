import { createContext, useContext } from 'react'
import type { TFunction } from 'i18next'

import type { Me } from '../api/types'

/** "unreachable": a session is stored but the server could not confirm it (offline). */
export type AuthStatus = 'loading' | 'signed-in' | 'signed-out' | 'unreachable'

export interface AuthState {
  user: Me | null
  status: AuthStatus
  /** Why the user is on the login page, e.g. the session expired (an i18n key). */
  notice: Parameters<TFunction>[0] | null
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  retry: () => void
}

export const AuthContext = createContext<AuthState | null>(null)

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
