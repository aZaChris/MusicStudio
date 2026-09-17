import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

import { apiFetch, tokenStorage } from '../api/client'

export type Role = 'teacher' | 'studio_owner' | 'parent'

export interface Me {
  id: number
  email: string
  role: Role
  preferred_language: 'en' | 'it'
  teacher: { id: number; studio: number | null; is_owner: boolean } | null
  parent_account: { id: number } | null
}

interface AuthState {
  user: Me | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Me | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const loadMe = async () => {
    if (!tokenStorage.getAccess()) {
      setUser(null)
      setIsLoading(false)
      return
    }
    try {
      const me = await apiFetch<Me>('/auth/me/')
      setUser(me)
    } catch {
      tokenStorage.clear()
      setUser(null)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadMe()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const login = async (email: string, password: string) => {
    const tokens = await apiFetch<{ access: string; refresh: string }>('/auth/token/', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    tokenStorage.set(tokens.access, tokens.refresh)
    await loadMe()
  }

  const logout = () => {
    tokenStorage.clear()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>{children}</AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
