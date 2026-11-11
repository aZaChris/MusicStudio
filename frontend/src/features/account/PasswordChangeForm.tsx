import { useMutation } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

import { apiFetch } from '../../api/client'
import { ErrorText } from '../../components/QueryState'
import { useAuth } from '../../auth/useAuth'

/** Changing the password ends every session, this one included: the user signs in again. */
export function PasswordChangeForm() {
  const { t } = useTranslation()
  const { logout } = useAuth()
  const navigate = useNavigate()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const change = useMutation({
    mutationFn: () =>
      apiFetch('/auth/password/change/', {
        method: 'POST',
        body: { current_password: current, new_password: next },
      }),
    onSuccess: async () => {
      await logout() // the server already revoked the tokens; this clears the local state
      navigate('/login')
    },
  })

  const submit = (e: FormEvent) => {
    e.preventDefault()
    change.mutate()
  }

  return (
    <form className="ms-form" onSubmit={submit}>
      <h2 className="section-title">{t('account.changePassword')}</h2>
      <p className="ms-help" style={{ margin: 0 }}>
        {t('account.changePasswordHint')}
      </p>
      <label className="ms-field">
        {t('account.currentPassword')}
        <input
          className="ms-input"
          type="password"
          autoComplete="current-password"
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
          required
        />
      </label>
      <label className="ms-field">
        {t('reset.newPassword')}
        <input
          className="ms-input"
          type="password"
          autoComplete="new-password"
          value={next}
          onChange={(e) => setNext(e.target.value)}
          required
        />
      </label>
      <ErrorText error={change.error} />
      <button type="submit" className="ms-btn ms-btn--primary" disabled={change.isPending}>
        {t('account.changePasswordSubmit')}
      </button>
    </form>
  )
}
