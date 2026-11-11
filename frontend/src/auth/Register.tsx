import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { apiFetch } from '../api/client'
import { errorMessage } from '../api/errors'
import type { RegisterRequest } from '../api/types'
import { AuthLayout, FormError, FormNotice } from './AuthLayout'

/** Studio owner sign-up. The answer is always "check your email", whatever the address. */
export function Register() {
  const { t, i18n } = useTranslation()
  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    email: '',
    password: '',
    studio_name: '',
    accept_terms: false,
  })
  const [error, setError] = useState<string | null>(null)
  const [sent, setSent] = useState(false)

  const set = (field: keyof typeof form) => (e: { target: { value: string; checked?: boolean } }) =>
    setForm({ ...form, [field]: field === 'accept_terms' ? Boolean(e.target.checked) : e.target.value })

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    const body: RegisterRequest = {
      ...form,
      preferred_language: i18n.language.startsWith('it') ? 'it' : 'en',
    }
    try {
      await apiFetch('/auth/register/', { method: 'POST', body, auth: false })
      setSent(true)
    } catch (err) {
      setError(errorMessage(err, t))
    }
  }

  if (sent) {
    return (
      <AuthLayout title={t('register.checkEmailTitle')}>
        <FormNotice message={t('register.checkEmail')} />
        <Link to="/login">{t('auth.backToLogin')}</Link>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout title={t('register.title')} hint={t('register.hint')}>
      <form className="ms-form" style={{ gap: 16 }} onSubmit={submit}>
        <label className="ms-field">
          {t('register.firstName')}
          <input className="ms-input" value={form.first_name} onChange={set('first_name')} required />
        </label>
        <label className="ms-field">
          {t('register.lastName')}
          <input className="ms-input" value={form.last_name} onChange={set('last_name')} required />
        </label>
        <label className="ms-field">
          {t('register.studioName')}
          <input className="ms-input" value={form.studio_name} onChange={set('studio_name')} required />
        </label>
        <label className="ms-field">
          {t('auth.email')}
          <input
            className="ms-input"
            type="email"
            autoComplete="username"
            value={form.email}
            onChange={set('email')}
            required
          />
        </label>
        <label className="ms-field">
          {t('auth.password')}
          <input
            className="ms-input"
            type="password"
            autoComplete="new-password"
            value={form.password}
            onChange={set('password')}
            required
          />
        </label>
        <label className="ms-field" style={{ flexDirection: 'row', gap: 8, alignItems: 'center' }}>
          <input type="checkbox" checked={form.accept_terms} onChange={set('accept_terms')} required />
          <span>{t('register.acceptTerms')}</span>
        </label>
        <FormError message={error} />
        <button type="submit" className="ms-btn ms-btn--primary ms-btn--l ms-btn--block">
          {t('register.submit')}
        </button>
        <Link to="/login">{t('register.haveAccount')}</Link>
      </form>
    </AuthLayout>
  )
}
