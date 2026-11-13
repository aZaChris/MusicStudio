// Theme and language switches: icon-only, fixed size, both options always visible. The old
// text buttons ("Chiaro"/"Scuro", "IT"/"EN") changed width on every click and shifted their
// neighbours; here nothing changes size, only which option is highlighted.
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import { useTheme } from '../theme/useTheme'
import { Icon } from './ui'

type Option<T extends string> = { value: T; label: string; lang?: string; icon: ReactNode }

function Segmented<T extends string>({
  label,
  options,
  value,
  onChange,
  onPlum,
}: {
  label: string
  options: Option<T>[]
  value: T
  onChange: (value: T) => void
  onPlum?: boolean
}) {
  return (
    <div className={`ms-seg${onPlum ? ' ms-seg--on-plum' : ''}`} role="group" aria-label={label}>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          lang={o.lang}
          title={o.label}
          aria-label={o.label}
          aria-pressed={o.value === value}
          onClick={() => o.value !== value && onChange(o.value)}
        >
          {o.icon}
        </button>
      ))}
    </div>
  )
}

export function ThemeToggle({ onPlum }: { onPlum?: boolean }) {
  const { t } = useTranslation()
  const { theme, toggleTheme } = useTheme()
  return (
    <Segmented
      label={t('theme.toggle')}
      onPlum={onPlum}
      value={theme}
      onChange={toggleTheme}
      options={[
        { value: 'light', label: t('theme.light'), icon: <Icon name="sun" size={18} /> },
        { value: 'dark', label: t('theme.dark'), icon: <Icon name="moon" size={18} /> },
      ]}
    />
  )
}

function FlagIT() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
      <clipPath id="ms-flag-clip">
        <circle cx="12" cy="12" r="12" />
      </clipPath>
      <g clipPath="url(#ms-flag-clip)">
        <rect width="8" height="24" fill="#009246" />
        <rect x="8" width="8" height="24" fill="#ffffff" />
        <rect x="16" width="8" height="24" fill="#ce2b37" />
      </g>
    </svg>
  )
}

function FlagEN() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
      <clipPath id="ms-flag-clip-en">
        <circle cx="12" cy="12" r="12" />
      </clipPath>
      <g clipPath="url(#ms-flag-clip-en)">
        <rect width="24" height="24" fill="#012169" />
        <path d="M0 0 24 24M24 0 0 24" stroke="#ffffff" strokeWidth="5" />
        <path d="M0 0 24 24M24 0 0 24" stroke="#c8102e" strokeWidth="2" />
        <path d="M12 0v24M0 12h24" stroke="#ffffff" strokeWidth="8" />
        <path d="M12 0v24M0 12h24" stroke="#c8102e" strokeWidth="4.5" />
      </g>
    </svg>
  )
}

export function LanguageToggle({ onPlum }: { onPlum?: boolean }) {
  const { t, i18n } = useTranslation()
  const current = i18n.language.startsWith('it') ? 'it' : 'en'
  return (
    <Segmented
      label={t('auth.language')}
      onPlum={onPlum}
      value={current}
      onChange={(lng) => i18n.changeLanguage(lng)}
      options={[
        { value: 'it', label: 'Italiano', lang: 'it', icon: <FlagIT /> },
        { value: 'en', label: 'English', lang: 'en', icon: <FlagEN /> },
      ]}
    />
  )
}
