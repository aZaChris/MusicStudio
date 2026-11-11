import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useState, type ReactNode } from 'react'

import { ApiError, apiFetch, session } from '../api/client'
import type { LoginResponse, Me, TokenPair } from '../api/types'
import { AuthContext, type AuthState, type AuthStatus } from './useAuth'

type CheckResult = { user: Me | null; status: AuthStatus }

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [user, setUser] = useState<Me | null>(null)
  const [status, setStatus] = useState<AuthStatus>('loading')
  const [notice, setNotice] = useState<AuthState['notice']>(null)

  // Page load: never trust a cached user; ask the server who we are.
  const check = useCallback(async (): Promise<CheckResult> => {
    if (!session.refreshToken()) return { user: null, status: 'signed-out' }
    try {
      return { user: await apiFetch<Me>('/auth/me/'), status: 'signed-in' }
    } catch (error) {
      if (error instanceof ApiError && error.status === 0) return { user: null, status: 'unreachable' }
      session.clear()
      return { user: null, status: 'signed-out' }
    }
  }, [])

  const apply = useCallback((result: CheckResult) => {
    setUser(result.user)
    setStatus(result.status)
  }, [])

  useEffect(() => {
    let mounted = true
    void check().then((result) => mounted && apply(result))
    return () => {
      mounted = false
    }
  }, [check, apply])

  // The client could not renew the session: back to login, and drop every cached response.
  useEffect(
    () =>
      session.onExpired(() => {
        queryClient.clear()
        setUser(null)
        setNotice('auth.sessionExpired')
        setStatus('signed-out')
      }),
    [queryClient],
  )

  const finishSignIn = useCallback(
    async (tokens: { access: string; refresh: string }) => {
      session.start(tokens)
      const me = await apiFetch<Me>('/auth/me/')
      queryClient.clear() // nothing from a previous user survives a sign-in
      setUser(me)
      setNotice(null)
      setStatus('signed-in')
    },
    [queryClient],
  )

  const login = useCallback(
    async (email: string, password: string) => {
      const answer = await apiFetch<LoginResponse>('/auth/token/', {
        method: 'POST',
        body: { email, password },
        auth: false,
      })
      // Owners and teachers with MFA on get a short-lived token instead of the pair.
      if (answer.mfa_required && answer.mfa_token) return { mfaToken: answer.mfa_token }
      await finishSignIn(answer as TokenPair)
      return { mfaToken: null }
    },
    [finishSignIn],
  )

  const verifyMfa = useCallback(
    async (mfaToken: string, code: string) => {
      const tokens = await apiFetch<TokenPair>('/auth/mfa/verify/', {
        method: 'POST',
        body: { mfa_token: mfaToken, code },
        auth: false,
      })
      await finishSignIn(tokens)
    },
    [finishSignIn],
  )

  const logout = useCallback(async () => {
    // The body is read at send time: with an expired access token the first call refreshes,
    // which rotates the refresh token, so its body carries the old, now blacklisted, token
    // and gets 400. The second call sends the rotated one.
    const sendLogout = async () => {
      const refresh = session.refreshToken()
      if (refresh) await apiFetch('/auth/logout/', { method: 'POST', body: { refresh } })
    }
    try {
      await sendLogout()
    } catch (error) {
      if (error instanceof ApiError && error.status === 400) await sendLogout().catch(() => undefined)
      // Any other failure (offline...): still sign out locally, as the user asked.
    }
    session.clear()
    queryClient.clear()
    setUser(null)
    setNotice(null)
    setStatus('signed-out')
  }, [queryClient])

  const retry = useCallback(() => {
    setStatus('loading')
    void check().then(apply)
  }, [check, apply])

  return (
    <AuthContext.Provider value={{ user, status, notice, login, verifyMfa, logout, retry }}>
      {children}
    </AuthContext.Provider>
  )
}
