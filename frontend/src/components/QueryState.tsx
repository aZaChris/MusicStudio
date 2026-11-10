import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import { errorMessage } from '../api/errors'

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
  if (query.isPending) return <p aria-busy="true">{t('common.loading')}</p>
  if (query.isError) {
    return (
      <div role="alert" style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        <span style={{ color: 'var(--ms-danger-text)' }}>{errorMessage(query.error, t)}</span>
        <button type="button" onClick={() => query.refetch()}>
          {t('common.retry')}
        </button>
      </div>
    )
  }
  if (isEmpty) return <p style={{ color: 'var(--ms-text-muted)' }}>{emptyText}</p>
  return <>{children}</>
}

/** Inline error next to a form or dialog action. */
export function ErrorText({ error }: { error: unknown }) {
  const { t } = useTranslation()
  if (!error) return null
  return (
    <p role="alert" style={{ color: 'var(--ms-danger-text)', margin: 0 }}>
      {errorMessage(error, t)}
    </p>
  )
}
