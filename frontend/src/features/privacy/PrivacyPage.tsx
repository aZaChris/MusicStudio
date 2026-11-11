import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'

import { apiFetch } from '../../api/client'
import type { components } from '../../api/schema'
import { useAuth } from '../../auth/useAuth'
import { ErrorText, QueryState } from '../../components/QueryState'
import { Icon } from '../../components/ui'
import { formatDay } from '../../lib/dates'
import { PasswordChangeForm } from '../account/PasswordChangeForm'

type Consent = components['schemas']['Consent']

/** Parents and adult students: consents, a copy of their data, and closing the account. */
export function PrivacyPage() {
  const { t, i18n } = useTranslation()
  const { logout } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const consents = useQuery({
    queryKey: ['consents'],
    queryFn: () => apiFetch<Consent[]>('/privacy/consents/'),
  })
  const [password, setPassword] = useState('')
  const [confirmErase, setConfirmErase] = useState(false)

  const download = useMutation({
    mutationFn: () => apiFetch<unknown>('/privacy/export/'),
    onSuccess: (data) => {
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }))
      const link = document.createElement('a')
      link.href = url
      link.download = 'musicstudio-export.json'
      link.click()
      URL.revokeObjectURL(url)
    },
  })
  const withdraw = useMutation({
    mutationFn: (id: number) =>
      apiFetch(`/privacy/consents/${id}/withdraw/`, { method: 'POST', body: { password } }),
    onSuccess: () => {
      setPassword('')
      void queryClient.invalidateQueries() // the children are gone from the lists
    },
  })
  const erase = useMutation({
    mutationFn: () => apiFetch('/privacy/erase/', { method: 'POST', body: { password } }),
    onSuccess: async () => {
      await logout()
      navigate('/login')
    },
  })

  return (
    <main className="portal-main">
      <Link to="/" className="back-link">
        <Icon name="back" size={18} />
        {t('privacy.back')}
      </Link>
      <h1 className="page-title">{t('privacy.title')}</h1>

      <section className="panel">
        <h2 className="section-title">{t('privacy.consents')}</h2>
        <QueryState
          query={consents}
          isEmpty={consents.data?.length === 0}
          emptyText={t('privacy.noConsents')}
        >
          <ul className="ms-stack" style={{ listStyle: 'none', padding: 0 }}>
            {consents.data?.map((c) => (
              <li key={c.id} className="list-line">
                <span className="list-line__main">
                  <strong>{c.children.map((child) => child.name).join(', ')}</strong>
                  <span className="muted">
                    {t('privacy.givenOn', {
                      date: formatDay(c.given_at, i18n.language),
                      version: c.notice_version,
                    })}
                  </span>
                </span>
                {c.withdrawn_at ? (
                  <span className="muted">{t('privacy.withdrawn')}</span>
                ) : (
                  <button
                    type="button"
                    className="ms-btn ms-btn--secondary"
                    disabled={!password}
                    onClick={() => withdraw.mutate(c.id)}
                  >
                    {t('privacy.withdraw')}
                  </button>
                )}
              </li>
            ))}
          </ul>
        </QueryState>
        <ErrorText error={withdraw.error} />
      </section>

      <section className="panel">
        <h2 className="section-title">{t('privacy.exportTitle')}</h2>
        <p className="ms-help" style={{ margin: 0 }}>
          {t('privacy.exportHint')}
        </p>
        <button type="button" className="ms-btn ms-btn--secondary" onClick={() => download.mutate()}>
          {t('privacy.download')}
        </button>
        <ErrorText error={download.error} />
      </section>

      <section className="panel">
        <h2 className="section-title">{t('privacy.eraseTitle')}</h2>
        <p className="ms-alert ms-alert--warning" style={{ margin: 0 }}>
          {t('privacy.eraseWarning')}
        </p>
        <label className="ms-field">
          {t('privacy.passwordToConfirm')}
          <input
            className="ms-input"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        <label className="ms-check">
          <input type="checkbox" checked={confirmErase} onChange={(e) => setConfirmErase(e.target.checked)} />
          {t('privacy.eraseConfirm')}
        </label>
        <ErrorText error={erase.error} />
        <button
          type="button"
          className="ms-btn ms-btn--primary"
          disabled={!password || !confirmErase || erase.isPending}
          onClick={() => erase.mutate()}
        >
          {t('privacy.erase')}
        </button>
      </section>

      <section className="panel">
        <PasswordChangeForm />
      </section>
    </main>
  )
}
