import { useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router-dom'

import { ApiError } from '../../api/client'
import { ErrorText } from '../../components/QueryState'
import { goToExternal } from '../../lib/navigate'
import {
  usePaymentAccount,
  useRefreshAccount,
  useRestartAccount,
  useStartOnboarding,
} from '../teacher/api/paymentAccount'

/**
 * Online payments straight to the studio's own Stripe account. MusicStudio never holds the money:
 * the owner opens (or finishes) the account on Stripe's own page, and the state shown here is what
 * Stripe reports. Teachers only read. While the feature is off the server answers 404 and the
 * whole section is simply not there.
 */
export function PaymentAccountSection({ canEdit }: { canEdit: boolean }) {
  const { t, i18n } = useTranslation()
  const account = usePaymentAccount()
  const start = useStartOnboarding()
  const refresh = useRefreshAccount()
  const restart = useRestartAccount()
  const [params, setParams] = useSearchParams()
  const handledReturn = useRef(false)

  // Coming back from Stripe's page (?return=1): read the account once, then clean the address.
  const returned = params.get('return') === '1'
  const refreshNow = refresh.mutate
  useEffect(() => {
    if (!canEdit || !returned || handledReturn.current) return
    handledReturn.current = true
    refreshNow()
    setParams({}, { replace: true })
  }, [canEdit, returned, refreshNow, setParams])

  if (account.isError && account.error instanceof ApiError && account.error.status === 404) {
    return null
  }
  if (account.isPending) return null
  if (account.isError) return <ErrorText error={account.error} />

  const data = account.data
  const goToStripe = () => start.mutate(undefined, { onSuccess: (link) => goToExternal(link.url) })
  const startAgain = () => restart.mutate(undefined, { onSuccess: goToStripe })
  const date = new Intl.DateTimeFormat(i18n.language, { dateStyle: 'medium' })

  return (
    <section className="panel ms-stack" aria-labelledby="payment-account-title">
      <h2 id="payment-account-title" className="section-title">
        {t('paymentAccount.title')}
      </h2>
      <p className="muted">{t('paymentAccount.intro')}</p>
      {data.test_mode && (
        <p role="note" className="ms-alert ms-alert--warning" style={{ margin: 0 }}>
          {t('paymentAccount.testMode')}
        </p>
      )}
      <p>
        <strong>{t('paymentAccount.stateLabel')}: </strong>
        <span data-testid="account-state">{t(`paymentAccount.state.${data.state}`)}</span>
      </p>
      <p className="muted">{t(`paymentAccount.hint.${data.state}`)}</p>

      {canEdit ? (
        <div className="ms-row">
          {data.state === 'disconnected' ? (
            <button type="button" className="ms-btn ms-btn--primary" onClick={startAgain}>
              {t('paymentAccount.startAgain')}
            </button>
          ) : data.state === 'active' ? (
            <button
              type="button"
              className="ms-btn ms-btn--secondary"
              disabled={refresh.isPending}
              onClick={() => refresh.mutate()}
            >
              {t('paymentAccount.check')}
            </button>
          ) : (
            <button
              type="button"
              className="ms-btn ms-btn--primary"
              disabled={start.isPending}
              onClick={goToStripe}
            >
              {data.state === 'not_started' ? t('paymentAccount.start') : t('paymentAccount.continue')}
            </button>
          )}
          {data.dashboard_url && (
            <a
              className="ms-btn ms-btn--secondary"
              href={data.dashboard_url}
              target="_blank"
              rel="noreferrer"
            >
              {t('paymentAccount.openStripe')}
            </a>
          )}
        </div>
      ) : (
        <p role="note" className="ms-alert ms-alert--warning" style={{ margin: 0 }}>
          {t('paymentAccount.readOnly')}
        </p>
      )}
      <ErrorText error={start.error ?? refresh.error ?? restart.error} />

      {data.needs_attention.length > 0 && (
        <div>
          <h3 className="section-title">{t('paymentAccount.attentionTitle')}</h3>
          <p className="muted">{t('paymentAccount.attentionIntro')}</p>
          <ul>
            {data.needs_attention.map((item) => (
              <li key={item.id}>
                {t(`paymentAccount.attention.${item.kind}`, { defaultValue: item.kind })}
                {item.amount ? ` — ${item.amount} €` : ''} ({date.format(new Date(item.received_at))})
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}
