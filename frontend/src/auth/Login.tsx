import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, useNavigate } from 'react-router-dom'

import { ApiError } from '../api/client'
import { errorMessage } from '../api/errors'
import { useAuth } from './useAuth'

export function Login() {
  const { t } = useTranslation()
  const { user, notice, login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)

  if (user) return <Navigate to="/" replace />

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      await login(email, password)
      navigate('/')
    } catch (err) {
      // 401 on login = wrong credentials; anything else (offline, throttled) says what it is.
      setError(
        err instanceof ApiError && err.status === 401 ? t('auth.invalidCredentials') : errorMessage(err, t),
      )
    }
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', alignItems: 'center', justifyContent: 'center' }}>
      <form
        onSubmit={handleSubmit}
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
          width: 320,
          padding: 28,
          borderRadius: 'var(--ms-radius-lg)',
          border: '1px solid var(--ms-border)',
          background: 'var(--ms-surface)',
        }}
      >
        <h1 style={{ fontFamily: 'var(--ms-font-heading)', fontSize: 20, margin: 0 }}>MusicStudio</h1>
        <label>
          {t('auth.email')}
          <input
            type="email"
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>
        <label>
          {t('auth.password')}
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
        {notice && !error && (
          <p role="status" style={{ color: 'var(--ms-warning-text)', margin: 0 }}>
            {t(notice)}
          </p>
        )}
        {error && (
          <p role="alert" style={{ color: 'var(--ms-danger-text)', margin: 0 }}>
            {error}
          </p>
        )}
        <button type="submit">{t('auth.login')}</button>
      </form>
    </div>
  )
}
