import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import type { Student } from '../../api/types'
import { AppShell } from '../../components/AppShell'
import { QueryState } from '../../components/QueryState'
import { Avatar, Beats, Icon, StatusChip } from '../../components/ui'
import { paymentTone } from '../../components/tones'
import { useStudents } from './api/students'

type Filter = 'all' | 'low' | 'none'
const FILTERS: Filter[] = ['all', 'low', 'none']

function matches(student: Student, filter: Filter, query: string) {
  if (filter === 'low' && !student.active_package?.is_low) return false
  if (filter === 'none' && student.active_package) return false
  const needle = query.trim().toLowerCase()
  return !needle || `${student.full_name} ${student.instrument}`.toLowerCase().includes(needle)
}

export function Roster() {
  const { t } = useTranslation()
  const students = useStudents()
  const list = students.data ?? []
  const [filter, setFilter] = useState<Filter>('all')
  const [query, setQuery] = useState('')
  const shown = list.filter((s) => matches(s, filter, query))

  return (
    <AppShell>
      <div className="page-head">
        <div className="page-head__text">
          <span className="page-eyebrow">{t('roster.activeCount', { count: list.length })}</span>
          <h1 className="page-title">{t('roster.title')}</h1>
        </div>
        <label className="ms-search">
          <Icon name="search" size={18} />
          <input
            type="search"
            aria-label={t('roster.search')}
            placeholder={t('roster.searchPlaceholder')}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
      </div>

      <div className="ms-filters">
        {FILTERS.map((f) => (
          <button
            key={f}
            type="button"
            className="ms-filter"
            aria-pressed={filter === f}
            onClick={() => setFilter(f)}
          >
            {t(`roster.filter.${f}`)}
          </button>
        ))}
      </div>

      <QueryState query={students} isEmpty={list.length === 0} emptyText={t('roster.empty')}>
        {shown.length === 0 ? (
          <p className="muted">{t('roster.noMatch')}</p>
        ) : (
          <div className="card-grid">
            {shown.map((student, i) => {
              const pkg = student.active_package
              return (
                <Link key={student.id} to={`/students/${student.id}`} className="ms-card card-link">
                  <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
                    <Avatar name={student.full_name} index={i} />
                    <div className="list-line__main" style={{ flex: 1 }}>
                      <span style={{ fontSize: 17, fontWeight: 700 }}>{student.full_name}</span>
                      <span className="muted">{student.instrument}</span>
                    </div>
                  </div>
                  {pkg ? (
                    <div className="ms-stack" style={{ gap: 8 }}>
                      <Beats total={pkg.total_lessons} used={pkg.total_lessons - pkg.lessons_remaining} />
                      <div className="row-between">
                        <span className="ms-beats-label">
                          {t('roster.remainingOf', {
                            remaining: pkg.lessons_remaining,
                            total: pkg.total_lessons,
                          })}
                        </span>
                        {pkg.is_low && (
                          <StatusChip tone="low" small>
                            {t('roster.lowPackage')}
                          </StatusChip>
                        )}
                      </div>
                    </div>
                  ) : (
                    <StatusChip tone="off">{t('roster.noPackage')}</StatusChip>
                  )}
                  {student.payment_status && (
                    <div>
                      <StatusChip tone={paymentTone(student.payment_status)} small>
                        {t(`payments.statusName.${student.payment_status}`)}
                      </StatusChip>
                    </div>
                  )}
                </Link>
              )
            })}
          </div>
        )}
      </QueryState>
    </AppShell>
  )
}
