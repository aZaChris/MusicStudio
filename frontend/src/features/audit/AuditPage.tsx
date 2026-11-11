import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { apiFetch } from '../../api/client'
import type { components } from '../../api/schema'
import { AppShell } from '../../components/AppShell'
import { QueryState } from '../../components/QueryState'
import { formatDateTime } from '../../lib/dates'

type Entry = components['schemas']['AuditEntry']
type Page = components['schemas']['PaginatedAuditEntryList']

const ACTIONS: components['schemas']['ActionEnum'][] = [
  'login.success',
  'login.failure',
  'login.locked',
  'password.reset',
  'password.change',
  'mfa.enable',
  'mfa.disable',
  'invitation.send',
  'invitation.accept',
  'invitation.revoke',
  'consent.give',
  'consent.withdraw',
  'privacy.export',
  'privacy.erase',
  'payment.record',
]

/** Who did what in the studio, newest first, with an action and a day filter. */
export function AuditPage() {
  const { t, i18n } = useTranslation()
  const [action, setAction] = useState('')
  const [since, setSince] = useState('')
  const [pageNumber, setPageNumber] = useState(1)

  const query = useQuery({
    queryKey: ['audit', action, since, pageNumber],
    queryFn: () => {
      const params = new URLSearchParams({ page: String(pageNumber) })
      if (action) params.set('action', action)
      if (since) params.set('since', `${since}T00:00:00Z`)
      return apiFetch<Page>(`/audit/?${params}`)
    },
  })
  const rows: Entry[] = query.data?.results ?? []

  return (
    <AppShell>
      <div className="page-head__text">
        <h1 className="page-title">{t('nav.audit')}</h1>
      </div>
      <section className="panel">
        <div className="ms-form__grid">
          <label className="ms-field">
            {t('audit.action')}
            <select
              className="ms-input"
              value={action}
              onChange={(e) => {
                setAction(e.target.value)
                setPageNumber(1)
              }}
            >
              <option value="">{t('audit.allActions')}</option>
              {ACTIONS.map((a) => (
                <option key={a} value={a}>
                  {t(`audit.actions.${a}`, a)}
                </option>
              ))}
            </select>
          </label>
          <label className="ms-field">
            {t('audit.since')}
            <input
              className="ms-input"
              type="date"
              value={since}
              onChange={(e) => {
                setSince(e.target.value)
                setPageNumber(1)
              }}
            />
          </label>
        </div>

        <QueryState query={query} isEmpty={rows.length === 0} emptyText={t('audit.empty')}>
          <table className="ms-table">
            <thead>
              <tr>
                <th>{t('audit.when')}</th>
                <th>{t('audit.action')}</th>
                <th>{t('audit.who')}</th>
                <th>{t('audit.outcome')}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td>{formatDateTime(row.created_at, i18n.language)}</td>
                  <td>{t(`audit.actions.${row.action}`, row.action)}</td>
                  <td>{row.actor_email ?? '—'}</td>
                  <td>{t(`audit.outcomes.${row.outcome ?? 'success'}`)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="row-between">
            <button
              type="button"
              className="ms-btn ms-btn--secondary"
              disabled={pageNumber === 1}
              onClick={() => setPageNumber(pageNumber - 1)}
            >
              {t('audit.previous')}
            </button>
            <button
              type="button"
              className="ms-btn ms-btn--secondary"
              disabled={!query.data?.next}
              onClick={() => setPageNumber(pageNumber + 1)}
            >
              {t('audit.next')}
            </button>
          </div>
        </QueryState>
      </section>
    </AppShell>
  )
}
