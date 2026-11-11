import { useTranslation } from 'react-i18next'

import { AppShell } from '../../components/AppShell'
import { MfaPanel } from './MfaPanel'
import { PasswordChangeForm } from './PasswordChangeForm'

/** Owners and teachers: password and two-step verification. */
export function AccountPage() {
  const { t } = useTranslation()
  return (
    <AppShell>
      <div className="page-head__text">
        <h1 className="page-title">{t('nav.account')}</h1>
      </div>
      <div className="two-col">
        <section className="panel">
          <PasswordChangeForm />
        </section>
        <section className="panel">
          <MfaPanel />
        </section>
      </div>
    </AppShell>
  )
}
