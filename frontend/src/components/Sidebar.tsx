import { useTranslation } from 'react-i18next'
import { Link, useLocation } from 'react-router-dom'

import { useAuth } from '../auth/useAuth'
import { useTheme } from '../theme/useTheme'

const NAV_ITEMS = [
  { to: '/', icon: '▤', key: 'nav.dashboard' as const },
  { to: '/students', icon: '☰', key: 'nav.students' as const },
  { to: '/payments', icon: '€', key: 'nav.payments' as const },
]

export function Sidebar() {
  const { t, i18n } = useTranslation()
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const location = useLocation()

  const toggleLanguage = () => i18n.changeLanguage(i18n.language.startsWith('it') ? 'en' : 'it')

  return (
    <nav
      style={{
        width: 232,
        flex: 'none',
        background: 'var(--ms-surface-muted)',
        borderRight: '1px solid var(--ms-border)',
        display: 'flex',
        flexDirection: 'column',
        padding: '24px 16px',
        gap: 28,
        minHeight: '100vh',
        // Padding inside the 100vh, or the logout card at the bottom falls below the fold.
        boxSizing: 'border-box',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '0 8px' }}>
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: 'var(--ms-radius-sm)',
            background: 'var(--ms-accent)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            fontSize: 18,
          }}
        >
          ♪
        </div>
        <div style={{ fontFamily: 'var(--ms-font-heading)', fontWeight: 600, fontSize: 17 }}>MusicStudio</div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.to}
            to={item.to}
            style={{
              cursor: 'pointer',
              padding: '10px 14px',
              borderRadius: 'var(--ms-radius-sm)',
              fontWeight: 700,
              fontSize: 14.5,
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              textDecoration: 'none',
              color: 'inherit',
              background: location.pathname === item.to ? 'var(--ms-border)' : 'transparent',
            }}
          >
            <span style={{ opacity: 0.75 }}>{item.icon}</span> {t(item.key)}
          </Link>
        ))}
      </div>

      <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={toggleTheme}
            title={t('theme.toggle')}
            aria-label={t('theme.toggle')}
            type="button"
          >
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>
          <button
            onClick={toggleLanguage}
            type="button"
            aria-label={i18n.language.startsWith('it') ? 'Switch to English' : 'Passa all’italiano'}
          >
            {i18n.language.startsWith('it') ? 'EN' : 'IT'}
          </button>
        </div>
        <div
          style={{
            padding: 14,
            borderRadius: 'var(--ms-radius-md)',
            background: 'var(--ms-border)',
            display: 'flex',
            flexDirection: 'column',
            gap: 2,
          }}
        >
          <div style={{ fontWeight: 800, fontSize: 13.5 }}>{user?.email}</div>
          <button onClick={logout} type="button" style={{ fontSize: 12.5, textAlign: 'left' }}>
            {t('auth.logout')}
          </button>
        </div>
      </div>
    </nav>
  )
}
