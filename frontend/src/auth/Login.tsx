import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, useNavigate } from 'react-router-dom'

import { useAuth } from './AuthProvider'

export function Login() {
  const { t } = useTranslation()
  const { user, login } = useAuth()
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
    } catch {
      setError('Invalid credentials')
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
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>
          {t('auth.password')}
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
        {error && <p style={{ color: 'var(--ms-danger-text)', margin: 0 }}>{error}</p>}
        <button type="submit">{t('auth.login')}</button>
      </form>
    </div>
  )
}
