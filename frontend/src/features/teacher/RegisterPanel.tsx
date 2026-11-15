import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { ErrorText, QueryState } from '../../components/QueryState'
import { localDateISO } from '../../lib/dates'
import { dayPeriod, isExportable, isValidPeriod, monthPeriod, type Period } from '../../lib/period'
import { useExportRegister, useRegisterSummary } from './api/payments'

type Mode = 'day' | 'month' | 'range'
const MODES: Mode[] = ['day', 'month', 'range']

/** The cash register's header: pick a period, read the totals, export for the accountant. */
export function RegisterPanel({
  period,
  onChange,
  money,
}: {
  period: Period
  onChange: (period: Period) => void
  money: Intl.NumberFormat
}) {
  const { t } = useTranslation()
  const today = localDateISO()
  const [mode, setMode] = useState<Mode>('month')
  const [day, setDay] = useState(today)
  const [month, setMonth] = useState(today.slice(0, 7))
  const [range, setRange] = useState<Period>(monthPeriod(today.slice(0, 7)))
  const summary = useRegisterSummary(period)
  const exporter = useExportRegister()

  const pick = (next: Mode) => {
    setMode(next)
    onChange(next === 'day' ? dayPeriod(day) : next === 'month' ? monthPeriod(month) : range)
  }
  const exportable = isExportable(period)

  return (
    <section className="panel" style={{ gap: 16 }} aria-label={t('register.title')}>
      <h2 className="section-title">{t('register.title')}</h2>
      <div className="ms-filters">
        {MODES.map((m) => (
          <button
            key={m}
            type="button"
            className="ms-filter"
            aria-pressed={mode === m}
            onClick={() => pick(m)}
          >
            {t(`register.mode.${m}`)}
          </button>
        ))}
      </div>

      <div className="ms-form__grid">
        {mode === 'day' && (
          <label className="ms-field">
            {t('payments.date')}
            <input
              className="ms-input"
              type="date"
              value={day}
              onChange={(e) => {
                setDay(e.target.value)
                if (e.target.value) onChange(dayPeriod(e.target.value))
              }}
            />
          </label>
        )}
        {mode === 'month' && (
          <label className="ms-field">
            {t('register.mode.month')}
            <input
              className="ms-input"
              type="month"
              value={month}
              onChange={(e) => {
                setMonth(e.target.value)
                if (e.target.value) onChange(monthPeriod(e.target.value))
              }}
            />
          </label>
        )}
        {mode === 'range' && (
          <>
            <label className="ms-field">
              {t('register.from')}
              <input
                className="ms-input"
                type="date"
                value={range.from}
                onChange={(e) => {
                  const next = { ...range, from: e.target.value }
                  setRange(next)
                  onChange(next)
                }}
              />
            </label>
            <label className="ms-field">
              {t('register.to')}
              <input
                className="ms-input"
                type="date"
                value={range.to}
                onChange={(e) => {
                  const next = { ...range, to: e.target.value }
                  setRange(next)
                  onChange(next)
                }}
              />
            </label>
          </>
        )}
      </div>
      {!isValidPeriod(period) && (
        <p role="alert" className="ms-alert ms-alert--error">
          {t('register.invalidPeriod')}
        </p>
      )}

      <QueryState query={summary} isEmpty={false} emptyText="">
        {summary.data && (
          <div className="ms-stack" style={{ gap: 12 }}>
            <dl
              style={{ display: 'flex', flexWrap: 'wrap', gap: 24, margin: 0 }}
              aria-label={t('register.totals')}
            >
              {(['received', 'reversed', 'net'] as const).map((key) => (
                <div key={key}>
                  <dt>{t(`register.${key}`)}</dt>
                  <dd className="num" style={{ margin: 0, fontWeight: 600 }}>
                    {money.format(Number(summary.data.totals[key]))}
                  </dd>
                </div>
              ))}
            </dl>
            <div className="ms-table-wrap">
              <table className="ms-table">
                <thead>
                  <tr>
                    <th scope="col">{t('payments.method')}</th>
                    <th scope="col" style={{ textAlign: 'right' }}>
                      {t('register.received')}
                    </th>
                    <th scope="col" style={{ textAlign: 'right' }}>
                      {t('register.reversed')}
                    </th>
                    <th scope="col" style={{ textAlign: 'right' }}>
                      {t('register.net')}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {summary.data.by_method.map((line) => (
                    <tr key={line.method}>
                      <td>{t(`payments.methodName.${line.method}`)}</td>
                      <td className="num">{money.format(Number(line.received))}</td>
                      <td className="num">{money.format(Number(line.reversed))}</td>
                      <td className="num">{money.format(Number(line.net))}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </QueryState>

      <div className="ms-filters">
        {(['csv', 'pdf'] as const).map((kind) => (
          <button
            key={kind}
            type="button"
            className="ms-btn ms-btn--secondary"
            disabled={!exportable || exporter.isPending}
            onClick={() => exporter.mutate({ kind, period })}
          >
            {t(`register.export.${kind}`)}
          </button>
        ))}
      </div>
      {isValidPeriod(period) && !exportable && (
        <p role="note" className="ms-alert ms-alert--warning" style={{ margin: 0 }}>
          {t('register.tooLong')}
        </p>
      )}
      <ErrorText error={exporter.error} />
    </section>
  )
}
