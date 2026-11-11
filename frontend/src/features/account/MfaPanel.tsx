import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { apiFetch } from '../../api/client'
import type { components } from '../../api/schema'
import { ErrorText, QueryState } from '../../components/QueryState'

type Status = components['schemas']['MfaStatus']
type Setup = components['schemas']['MfaSetup']
type Codes = components['schemas']['MfaRecoveryCodes']

/** Two-step verification for owners and teachers: set up, see recovery codes once, turn off. */
export function MfaPanel() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const status = useQuery({ queryKey: ['mfa'], queryFn: () => apiFetch<Status>('/auth/mfa/') })
  const [setup, setSetup] = useState<Setup | null>(null)
  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const [codes, setCodes] = useState<string[] | null>(null) // shown once, never stored
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['mfa'] })

  const start = useMutation({
    mutationFn: () => apiFetch<Setup>('/auth/mfa/setup/', { method: 'POST' }),
    onSuccess: setSetup,
  })
  const confirm = useMutation({
    mutationFn: () => apiFetch<Codes>('/auth/mfa/confirm/', { method: 'POST', body: { code } }),
    onSuccess: (res) => {
      setCodes(res.recovery_codes)
      setSetup(null)
      setCode('')
      void refresh()
    },
  })
  const disable = useMutation({
    mutationFn: () => apiFetch('/auth/mfa/disable/', { method: 'POST', body: { password, code } }),
    onSuccess: () => {
      setCode('')
      setPassword('')
      void refresh()
    },
  })
  const regenerate = useMutation({
    mutationFn: () =>
      apiFetch<Codes>('/auth/mfa/recovery-codes/', { method: 'POST', body: { password, code } }),
    onSuccess: (res) => {
      setCodes(res.recovery_codes)
      setCode('')
      setPassword('')
      void refresh()
    },
  })

  const codeField = (
    <label className="ms-field">
      {t('auth.mfaCode')}
      <input
        className="ms-input"
        autoComplete="one-time-code"
        value={code}
        onChange={(e) => setCode(e.target.value)}
        required
      />
    </label>
  )

  return (
    <section className="ms-stack" style={{ gap: 16 }}>
      <h2 className="section-title">{t('mfa.title')}</h2>
      <QueryState query={status}>
        {codes && (
          <div className="ms-alert ms-alert--warning" style={{ display: 'block' }}>
            <strong>{t('mfa.recoveryTitle')}</strong>
            <p style={{ margin: '4px 0' }}>{t('mfa.recoveryHint')}</p>
            <ul aria-label={t('mfa.recoveryTitle')}>
              {codes.map((c) => (
                <li key={c}>
                  <code>{c}</code>
                </li>
              ))}
            </ul>
            <button type="button" className="ms-btn ms-btn--secondary" onClick={() => setCodes(null)}>
              {t('mfa.savedCodes')}
            </button>
          </div>
        )}

        {!status.data?.enabled && !setup && (
          <>
            <p className="ms-help" style={{ margin: 0 }}>
              {t('mfa.off')}
            </p>
            <button type="button" className="ms-btn ms-btn--primary" onClick={() => start.mutate()}>
              {t('mfa.enable')}
            </button>
            <ErrorText error={start.error} />
          </>
        )}

        {setup && (
          <form
            className="ms-form"
            onSubmit={(e: FormEvent) => {
              e.preventDefault()
              confirm.mutate()
            }}
          >
            <p style={{ margin: 0 }}>{t('mfa.setupHint')}</p>
            <code aria-label={t('mfa.secret')}>{setup.secret}</code>
            <a href={setup.otpauth_uri}>{t('mfa.openApp')}</a>
            {codeField}
            <ErrorText error={confirm.error} />
            <button type="submit" className="ms-btn ms-btn--primary" disabled={confirm.isPending}>
              {t('mfa.confirm')}
            </button>
          </form>
        )}

        {status.data?.enabled && (
          <form className="ms-form" onSubmit={(e) => e.preventDefault()}>
            <p style={{ margin: 0 }}>{t('mfa.on', { count: status.data.recovery_codes_left })}</p>
            <label className="ms-field">
              {t('auth.password')}
              <input
                className="ms-input"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            {codeField}
            <ErrorText error={disable.error ?? regenerate.error} />
            <div className="page-actions">
              <button type="button" className="ms-btn ms-btn--secondary" onClick={() => regenerate.mutate()}>
                {t('mfa.newCodes')}
              </button>
              <button type="button" className="ms-btn ms-btn--secondary" onClick={() => disable.mutate()}>
                {t('mfa.disable')}
              </button>
            </div>
          </form>
        )}
      </QueryState>
    </section>
  )
}
