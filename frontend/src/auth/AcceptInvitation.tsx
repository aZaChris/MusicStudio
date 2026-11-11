import { useQuery } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { apiFetch, session } from '../api/client'
import { errorMessage } from '../api/errors'
import type { InvitationLookup, TokenPair } from '../api/types'
import { useAuth } from './useAuth'
import { AuthLayout, FormError, FormNotice } from './AuthLayout'

/** Opened from the invitation email: shows who invites, then sets a password and consent. */
export function AcceptInvitation() {
  const { t } = useTranslation()
  const { user, retry } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''
  const [form, setForm] = useState({ first_name: '', last_name: '', password: '' })
  const [terms, setTerms] = useState(false)
  const [consent, setConsent] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const lookup = useQuery({
    queryKey: ['invitation', token],
    queryFn: () =>
      apiFetch<InvitationLookup>(`/invitations/lookup/?token=${encodeURIComponent(token)}`, { auth: false }),
    retry: false,
  })

  if (lookup.isPending) return <AuthLayout title={t('invitation.title')}>{t('common.loading')}</AuthLayout>
  if (lookup.isError) {
    return (
      <AuthLayout title={t('invitation.title')}>
        <FormError message={t('invitation.invalid')} />
        <Link to="/login">{t('auth.backToLogin')}</Link>
      </AuthLayout>
    )
  }

  const invitation = lookup.data
  const isParent = invitation.role === 'parent'
  const signedInAsInvitee = user?.email.toLowerCase() === invitation.email.toLowerCase()

  if (invitation.existing_account && !signedInAsInvitee) {
    return (
      <AuthLayout title={t('invitation.title')}>
        <FormNotice message={t('invitation.signInFirst', { email: invitation.email })} />
        <Link to="/login">{t('auth.login')}</Link>
      </AuthLayout>
    )
  }

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      const tokens = await apiFetch<TokenPair>('/invitations/accept/', {
        method: 'POST',
        body: {
          token,
          ...(invitation.existing_account ? {} : form),
          accept_terms: terms,
          consent: isParent ? consent : false,
        },
        auth: signedInAsInvitee,
      })
      if (tokens?.access && tokens.refresh) session.start(tokens)
      retry() // re-check who we are with the new session
      navigate('/')
    } catch (err) {
      setError(errorMessage(err, t))
    }
  }

  return (
    <AuthLayout
      title={t('invitation.title')}
      hint={t('invitation.hint', {
        studio: invitation.studio_name,
        role: t(`invitation.role.${invitation.role}`),
      })}
    >
      <form className="ms-form" style={{ gap: 16 }} onSubmit={submit}>
        <p className="ms-help" style={{ margin: 0 }}>
          {invitation.email}
        </p>
        {isParent && invitation.student_first_names.length > 0 && (
          <p style={{ margin: 0 }}>
            {t('invitation.forStudents', { names: invitation.student_first_names.join(', ') })}
          </p>
        )}
        {!invitation.existing_account && (
          <>
            <label className="ms-field">
              {t('register.firstName')}
              <input
                className="ms-input"
                value={form.first_name}
                onChange={(e) => setForm({ ...form, first_name: e.target.value })}
                required
              />
            </label>
            <label className="ms-field">
              {t('register.lastName')}
              <input
                className="ms-input"
                value={form.last_name}
                onChange={(e) => setForm({ ...form, last_name: e.target.value })}
              />
            </label>
            <label className="ms-field">
              {t('auth.password')}
              <input
                className="ms-input"
                type="password"
                autoComplete="new-password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                required
              />
            </label>
          </>
        )}
        <label className="ms-field" style={{ flexDirection: 'row', gap: 8, alignItems: 'center' }}>
          <input type="checkbox" checked={terms} onChange={(e) => setTerms(e.target.checked)} required />
          <span>{t('register.acceptTerms')}</span>
        </label>
        {isParent && (
          <label className="ms-field" style={{ flexDirection: 'row', gap: 8, alignItems: 'center' }}>
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
              required
            />
            <span>{t('invitation.consent')}</span>
          </label>
        )}
        <FormError message={error} />
        <button type="submit" className="ms-btn ms-btn--primary ms-btn--l ms-btn--block">
          {t('invitation.accept')}
        </button>
      </form>
    </AuthLayout>
  )
}
