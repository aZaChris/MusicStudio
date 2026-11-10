// Small building blocks of the MusicStudio design system (design/system). Markup and class
// names follow design/system/components.css (`ms-*`); colours always come from tokens.
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

const ICONS = {
  home: <path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z" />,
  students: (
    <>
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.9" />
      <path d="M16 3.1a4 4 0 0 1 0 7.8" />
    </>
  ),
  payments: (
    <>
      <rect x="2" y="5" width="20" height="14" rx="2" />
      <line x1="2" y1="10" x2="22" y2="10" />
    </>
  ),
  logout: (
    <>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </>
  ),
  back: <polyline points="15 18 9 12 15 6" />,
  check: <polyline points="20 6 9 17 4 12" />,
  plus: (
    <>
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </>
  ),
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <line x1="21" y1="21" x2="16.6" y2="16.6" />
    </>
  ),
  alert: (
    <>
      <path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12" y2="17" />
    </>
  ),
  note: (
    <>
      <path d="M9 18V5l12-2v13" />
      <circle cx="6" cy="18" r="3" />
      <circle cx="18" cy="16" r="3" />
    </>
  ),
} as const

export type IconName = keyof typeof ICONS

/** Stroke icon on a 24px grid; takes its colour from the text (`currentColor`). */
export function Icon({ name, size = 20 }: { name: IconName; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {ICONS[name]}
    </svg>
  )
}

/** Double note on an orange square, plus the name. */
export function Logo({ size = 44 }: { size?: number }) {
  return (
    <span className="ms-logo">
      <span className="ms-logo__mark" style={{ width: size, height: size }}>
        <Icon name="note" size={Math.round(size * 0.55)} />
      </span>
      <span className="ms-logo__name">MusicStudio</span>
    </span>
  )
}

const AVATAR_TINTS = ['', 'orange', 'teal', 'peach', 'lilac'] as const

/** Initials on a rounded square; the colour follows the student's position in the list. */
export function Avatar({
  name,
  index = 0,
  size,
  circle = false,
}: {
  name: string
  index?: number
  size?: 's' | 'l'
  circle?: boolean
}) {
  const tint = AVATAR_TINTS[index % AVATAR_TINTS.length]
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()
  const cls = [
    'ms-avatar',
    tint && `ms-avatar--${tint}`,
    size && `ms-avatar--${size}`,
    circle && 'ms-avatar--circle',
  ]
  return (
    <span className={cls.filter(Boolean).join(' ')} aria-hidden="true">
      {initials}
    </span>
  )
}

/** One dot per lesson of a package: filled = already used. The signature element of the system. */
export function Beats({
  total,
  used,
  size,
  onPlum = false,
}: {
  total: number
  used: number
  size?: 's' | 'l'
  onPlum?: boolean
}) {
  const { t } = useTranslation()
  const cls = ['ms-beats', size && `ms-beats--${size}`, onPlum && 'ms-beats--on-plum']
  return (
    <div
      className={cls.filter(Boolean).join(' ')}
      role="img"
      aria-label={t('package.beats', { used, total })}
    >
      {Array.from({ length: total }, (_, i) => (
        <span key={i} className={i < used ? 'ms-beat ms-beat--on' : 'ms-beat'} />
      ))}
    </div>
  )
}

import type { Tone } from './tones'

/** A status pill. The text always says the state: colour alone never carries it. */
export function StatusChip({
  tone,
  small = false,
  children,
}: {
  tone: Tone
  small?: boolean
  children: ReactNode
}) {
  return <span className={`ms-chip ms-chip--${tone}${small ? ' ms-chip--s' : ''}`}>{children}</span>
}
