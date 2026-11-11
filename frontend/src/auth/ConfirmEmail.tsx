import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useSearchParams } from 'react-router-dom'

import { apiFetch } from '../api/client'
import { AuthLayout, FormError, FormNotice } from './AuthLayout'

/** Opened from the email link: sends `uid` and `token` to the backend, which decides. */
export function ConfirmEmail() {
  const { t } = useTranslation()
  const [params] = useSearchParams()
  const [state, setState] = useState<'working' | 'done' | 'failed'>('working')
  const started = useRef(false) // StrictMode runs effects twice; the link is single use

  useEffect(() => {
    if (started.current) return
    started.current = true
    apiFetch('/auth/confirm-email/', {
      method: 'POST',
      body: { uid: params.get('uid') ?? '', token: params.get('token') ?? '' },
      auth: false,
    }).then(
      () => setState('done'),
      () => setState('failed'),
    )
  }, [params])

  return (
    <AuthLayout title={t('confirm.title')}>
      {state === 'working' && <FormNotice message={t('confirm.working')} />}
      {state === 'done' && <FormNotice message={t('confirm.done')} />}
      {state === 'failed' && <FormError message={t('confirm.failed')} />}
      <Link to="/login">{t('auth.backToLogin')}</Link>
    </AuthLayout>
  )
}
