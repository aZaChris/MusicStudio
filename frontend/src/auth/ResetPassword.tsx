import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useSearchParams } from 'react-router-dom'

import { ApiError, apiFetch } from '../api/client'
import { errorMessage } from '../api/errors'
import { AuthLayout, FormError, FormNotice } from './AuthLayout'

export function ResetPassword() {
  const { t } = useTranslation()
  const [params] = useSearchParams()
  const [password, setPassword] = useState('')
  const [done, setDone] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      await apiFetch('/auth/password-reset/confirm/', {
        method: 'POST',
        body: {
          uid: params.get('uid') ?? '',
          token: params.get('token') ?? '',
          new_password: password,
        },
        auth: false,
      })
      setDone(true)
    } catch (err) {
      // A bad or used link comes back as a field error on `token`: say so plainly.
      setError(
        err instanceof ApiError && err.fieldErrors.token ? t('reset.linkInvalid') : errorMessage(err, t),
      )
    }
  }

  return (
    <AuthLayout title={t('reset.title')} hint={t('reset.hint')}>
      {done ? (
        <FormNotice message={t('reset.done')} />
      ) : (
        <form className="ms-form" style={{ gap: 16 }} onSubmit={submit}>
          <label className="ms-field">
            {t('reset.newPassword')}
            <input
              className="ms-input"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
          <FormError message={error} />
          <button type="submit" className="ms-btn ms-btn--primary ms-btn--l ms-btn--block">
            {t('reset.submit')}
          </button>
        </form>
      )}
      <Link to="/login">{t('auth.backToLogin')}</Link>
    </AuthLayout>
  )
}
