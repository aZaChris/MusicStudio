import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, Navigate, useNavigate } from 'react-router-dom'

import { ApiError, apiFetch } from '../api/client'
import { errorMessage } from '../api/errors'
import { LanguageToggle, ThemeToggle } from '../components/Preferences'
import { Icon, Logo } from '../components/ui'
import { useAuth } from './useAuth'

// Five staff lines with a few notes: decoration only, never behind text (design/system README).
const STAFF_LINES = [14, 34, 54, 74, 94]
const NOTES = [
  [120, 74],
  [220, 54],
  [320, 34],
  [420, 54],
]

export function Login() {
  const { t } = useTranslation()
  const { user, notice, login, verifyMfa } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [mfaToken, setMfaToken] = useState<string | null>(null)
  const [code, setCode] = useState('')
  const [unconfirmed, setUnconfirmed] = useState(false)
  const [resent, setResent] = useState(false)

  if (user) return <Navigate to="/" replace />

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setUnconfirmed(false)
    try {
      if (mfaToken) {
        await verifyMfa(mfaToken, code)
        navigate('/')
        return
      }
      const result = await login(email, password)
      if (result.mfaToken) setMfaToken(result.mfaToken)
      else navigate('/')
    } catch (err) {
      if (err instanceof ApiError && err.code === 'email_not_confirmed') {
        setUnconfirmed(true) // shown only after a correct password
        return
      }
      if (mfaToken && err instanceof ApiError && err.status === 401) {
        setError(t('auth.mfaInvalid'))
        return
      }
      // 401 on login = wrong credentials; anything else (offline, throttled) says what it is.
      setError(
        err instanceof ApiError && err.status === 401 ? t('auth.invalidCredentials') : errorMessage(err, t),
      )
    }
  }

  const resend = async () => {
    try {
      await apiFetch('/auth/confirm-email/resend/', { method: 'POST', body: { email }, auth: false })
      setResent(true)
    } catch (err) {
      setError(errorMessage(err, t))
    }
  }

  return (
    <div className="login-page">
      <section className="login-story">
        <Logo size={48} />
        <div className="ms-stack" style={{ gap: 18 }}>
          <h1>{t('auth.heroTitle')}</h1>
          <p>{t('auth.heroText')}</p>
        </div>
        <svg className="ms-staff" viewBox="0 0 600 110" preserveAspectRatio="none" aria-hidden="true">
          {STAFF_LINES.map((y) => (
            <line key={y} x1="0" y1={y} x2="600" y2={y} />
          ))}
          {NOTES.map(([cx, cy]) => (
            <ellipse
              key={cx}
              className="ms-staff__note"
              cx={cx}
              cy={cy}
              rx="11"
              ry="8"
              transform={`rotate(-20 ${cx} ${cy})`}
            />
          ))}
          <ellipse
            className="ms-staff__note ms-staff__note--accent"
            cx="520"
            cy="44"
            rx="11"
            ry="8"
            transform="rotate(-20 520 44)"
          />
        </svg>
      </section>

      <section className="login-form-side">
        <form className="ms-form" style={{ gap: 20 }} onSubmit={handleSubmit}>
          <div className="ms-stack" style={{ gap: 6 }}>
            <h2 style={{ fontSize: 32, fontWeight: 800 }}>{t('auth.login')}</h2>
            <p className="ms-help" style={{ margin: 0, fontSize: 16 }}>
              {t('auth.loginHint')}
            </p>
          </div>
          {mfaToken ? (
            <label className="ms-field">
              {t('auth.mfaCode')}
              <input
                className="ms-input"
                inputMode="text"
                autoComplete="one-time-code"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                required
              />
              <span className="ms-help">{t('auth.mfaHint')}</span>
            </label>
          ) : (
            <>
              <label className="ms-field">
                {t('auth.email')}
                <input
                  className="ms-input"
                  type="email"
                  autoComplete="username"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </label>
              <label className="ms-field">
                {t('auth.password')}
                <input
                  className="ms-input"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </label>
            </>
          )}
          {notice && !error && (
            <p role="status" className="ms-alert ms-alert--warning" style={{ margin: 0 }}>
              <Icon name="alert" size={18} />
              <span>{t(notice)}</span>
            </p>
          )}
          {unconfirmed && (
            <p role="alert" className="ms-alert ms-alert--warning" style={{ margin: 0 }}>
              <Icon name="alert" size={18} />
              <span>{resent ? t('auth.confirmationSent') : t('auth.notConfirmed')}</span>
              {!resent && (
                <button type="button" className="ms-btn ms-btn--secondary" onClick={resend}>
                  {t('auth.resendConfirmation')}
                </button>
              )}
            </p>
          )}
          {error && (
            <p role="alert" className="ms-alert ms-alert--error" style={{ margin: 0 }}>
              <Icon name="alert" size={18} />
              <span>{error}</span>
            </p>
          )}
          <button type="submit" className="ms-btn ms-btn--primary ms-btn--l ms-btn--block">
            {t('auth.login')}
          </button>
          {!mfaToken && (
            <div className="row-between">
              <Link to="/forgot-password">{t('auth.forgotPassword')}</Link>
              <Link to="/register">{t('auth.createAccount')}</Link>
            </div>
          )}
          <div className="row-between">
            <LanguageToggle />
            <ThemeToggle />
          </div>
        </form>
      </section>
    </div>
  )
}
