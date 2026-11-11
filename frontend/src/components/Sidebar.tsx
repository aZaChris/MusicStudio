import { useTranslation } from 'react-i18next'
import { Link, useLocation } from 'react-router-dom'

import { useAuth } from '../auth/useAuth'
import { useTheme } from '../theme/useTheme'
import { Avatar, Icon, Logo, type IconName } from './ui'

type NavKey = 'nav.dashboard' | 'nav.students' | 'nav.payments' | 'nav.team' | 'nav.audit' | 'nav.account'
const NAV_ITEMS: { to: string; icon: IconName; key: NavKey; ownerOnly?: boolean }[] = [
  { to: '/', icon: 'home', key: 'nav.dashboard' },
  { to: '/students', icon: 'students', key: 'nav.students' },
  { to: '/payments', icon: 'payments', key: 'nav.payments' },
  { to: '/team', icon: 'students', key: 'nav.team', ownerOnly: true },
  { to: '/audit', icon: 'check', key: 'nav.audit', ownerOnly: true },
  { to: '/account', icon: 'check', key: 'nav.account' },
]

export function Sidebar() {
  const { t, i18n } = useTranslation()
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const location = useLocation()

  const isItalian = i18n.language.startsWith('it')
  const toggleLanguage = () => i18n.changeLanguage(isItalian ? 'en' : 'it')
  // Students/:id belongs to the "Students" entry; "/" matches only itself.
  const isCurrent = (to: string) =>
    to === '/' ? location.pathname === '/' : location.pathname.startsWith(to)

  return (
    <aside className="ms-sidebar">
      <Logo size={40} />
      <nav className="ms-sidebar__nav" aria-label={t('nav.label')}>
        {NAV_ITEMS.filter((item) => !item.ownerOnly || user?.role === 'studio_owner').map((item) => (
          <Link
            key={item.to}
            to={item.to}
            className="ms-navlink"
            aria-current={isCurrent(item.to) ? 'page' : undefined}
          >
            <Icon name={item.icon} />
            {t(item.key)}
          </Link>
        ))}
      </nav>

      <div className="ms-sidebar__tools">
        <button
          type="button"
          className="ms-btn ms-btn--on-plum"
          onClick={toggleTheme}
          title={t('theme.toggle')}
          aria-label={t('theme.toggle')}
        >
          {theme === 'dark' ? t('theme.light') : t('theme.dark')}
        </button>
        <button
          type="button"
          className="ms-btn ms-btn--on-plum"
          onClick={toggleLanguage}
          aria-label={isItalian ? 'Switch to English' : 'Passa all’italiano'}
        >
          {isItalian ? 'EN' : 'IT'}
        </button>
      </div>

      <div className="ms-sidebar__foot">
        <Avatar name={user?.email ?? '?'} index={3} circle />
        <div className="ms-sidebar__foot-text">
          <span>{user?.email}</span>
          <span className="ms-sidebar__role">{user ? t(`auth.role.${user.role}`) : ''}</span>
        </div>
        <button type="button" className="ms-btn ms-btn--on-plum" onClick={logout}>
          {t('auth.logout')}
        </button>
      </div>
    </aside>
  )
}
