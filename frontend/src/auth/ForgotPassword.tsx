import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { apiFetch } from '../api/client'
import { errorMessage } from '../api/errors'
import { AuthLayout, FormError, FormNotice } from './AuthLayout'

/** Always the same answer, so the page never reveals whether an address is registered. */
export function ForgotPassword() {
  const { t } = useTranslation()
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      await apiFetch('/auth/password-reset/', { method: 'POST', body: { email }, auth: false })
      setSent(true)
    } catch (err) {
      setError(errorMessage(err, t))
    }
  }

  return (
    <AuthLayout title={t('forgot.title')} hint={t('forgot.hint')}>
      {sent ? (
        <FormNotice message={t('forgot.sent')} />
      ) : (
        <form className="ms-form" style={{ gap: 16 }} onSubmit={submit}>
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
          <FormError message={error} />
          <button type="submit" className="ms-btn ms-btn--primary ms-btn--l ms-btn--block">
            {t('forgot.submit')}
          </button>
        </form>
      )}
      <Link to="/login">{t('auth.backToLogin')}</Link>
    </AuthLayout>
  )
}
