import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { Icon } from '../../components/ui'

/**
 * Where Stripe sends the payer back to. They say nothing about the outcome of the payment: the
 * register is updated by Stripe's own confirmation (a webhook), not by this page. So the success
 * page only says "we are confirming it" and asks not to pay twice.
 */
function ReturnPage({ kind }: { kind: 'success' | 'cancel' }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  // Look at the lists once, in case the confirmation already arrived.
  useEffect(() => {
    void queryClient.invalidateQueries({ queryKey: ['payments'] })
    void queryClient.invalidateQueries({ queryKey: ['students'] })
  }, [queryClient])

  return (
    <main className="portal-main">
      <section className="panel ms-stack" role="status">
        <h1 className="page-title">
          <Icon name={kind === 'success' ? 'check' : 'alert'} size={24} /> {t(`payReturn.${kind}Title`)}
        </h1>
        <p>{t(`payReturn.${kind}Body`)}</p>
        <Link to="/" className="ms-btn ms-btn--primary">
          {t('payReturn.back')}
        </Link>
      </section>
    </main>
  )
}

export const PaymentSuccess = () => <ReturnPage kind="success" />
export const PaymentCancel = () => <ReturnPage kind="cancel" />
