import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import { errorMessage } from '../api/errors'
import { Icon } from './ui'

interface QueryLike {
  isPending: boolean
  isError: boolean
  error: unknown
  refetch: () => unknown
}

/** Loading, failure with retry, "nothing here", or the content: no page is ever silently blank. */
export function QueryState({
  query,
  isEmpty = false,
  emptyText,
  children,
}: {
  query: QueryLike
  isEmpty?: boolean
  emptyText?: string
  children: ReactNode
}) {
  const { t } = useTranslation()
  if (query.isPending) {
    // List-shaped placeholders instead of a spinner (design/system/motion.md).
    return (
      <div aria-busy="true" className="ms-stack">
        <span className="muted">{t('common.loading')}</span>
        <div className="ms-skeleton" />
        <div className="ms-skeleton" />
      </div>
    )
  }
  if (query.isError) {
    return (
      <div role="alert" className="ms-alert ms-alert--error" style={{ alignItems: 'center' }}>
        <Icon name="alert" size={18} />
        <span style={{ flex: 1 }}>{errorMessage(query.error, t)}</span>
        <button type="button" className="ms-btn ms-btn--secondary" onClick={() => query.refetch()}>
          {t('common.retry')}
        </button>
      </div>
    )
  }
  if (isEmpty) return <p className="muted">{emptyText}</p>
  return <>{children}</>
}

/** Inline error next to a form or dialog action. */
export function ErrorText({ error }: { error: unknown }) {
  const { t } = useTranslation()
  if (!error) return null
  return (
    <div role="alert" className="ms-alert ms-alert--error">
      <Icon name="alert" size={18} />
      <span>{errorMessage(error, t)}</span>
    </div>
  )
}
