import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { AppDownload } from '../components/AppDownload'
import { Beats, Icon, Logo, type IconName } from '../components/ui'
import { useTheme } from '../theme/useTheme'

const FEATURES: { key: 'lessons' | 'packages' | 'payments' | 'parents'; icon: IconName }[] = [
  { key: 'lessons', icon: 'home' },
  { key: 'packages', icon: 'note' },
  { key: 'payments', icon: 'payments' },
  { key: 'parents', icon: 'students' },
]
const SAFETY = ['studios', 'notes', 'rights', 'twoStep'] as const
const STEPS = ['account', 'students', 'parents'] as const

/** What a visitor sees before signing in: what the product is, and how to start. */
export function Landing() {
  const { t, i18n } = useTranslation()
  const { theme, toggleTheme } = useTheme()
  const isItalian = i18n.language.startsWith('it')

  return (
    <div className="landing">
      <header className="landing-bar">
        <Logo size={40} />
        <nav className="landing-bar__tools" aria-label={t('landing.nav')}>
          <button
            type="button"
            className="ms-btn ms-btn--secondary ms-btn--s"
            onClick={toggleTheme}
            aria-label={t('theme.toggle')}
          >
            {theme === 'dark' ? t('theme.light') : t('theme.dark')}
          </button>
          <button
            type="button"
            className="ms-btn ms-btn--secondary ms-btn--s"
            onClick={() => i18n.changeLanguage(isItalian ? 'en' : 'it')}
            aria-label={isItalian ? 'Switch to English' : 'Passa all’italiano'}
          >
            {isItalian ? 'EN' : 'IT'}
          </button>
          <Link to="/login" className="ms-btn ms-btn--secondary ms-btn--s">
            {t('auth.login')}
          </Link>
        </nav>
      </header>

      <main>
        <section className="landing-hero">
          <div className="landing-hero__text">
            <h1>{t('landing.heroTitle')}</h1>
            <p>{t('landing.heroText')}</p>
            <div className="page-actions">
              <Link to="/register" className="ms-btn ms-btn--primary ms-btn--l">
                {t('landing.start')}
              </Link>
              <Link to="/login" className="ms-btn ms-btn--on-plum ms-btn--l">
                {t('auth.login')}
              </Link>
            </div>
            <p className="landing-hero__hint">{t('landing.inviteHint')}</p>
          </div>
          <div className="landing-hero__card" aria-hidden="false">
            <span className="ms-label">{t('landing.sampleLabel')}</span>
            <Beats onPlum size="l" total={8} used={3} />
            <span className="landing-hero__number">{t('landing.sampleRemaining')}</span>
          </div>
        </section>

        <section className="landing-section" aria-labelledby="landing-features">
          <h2 id="landing-features">{t('landing.featuresTitle')}</h2>
          <div className="landing-grid">
            {FEATURES.map(({ key, icon }) => (
              <article key={key} className="panel">
                <span className="landing-icon">
                  <Icon name={icon} size={24} />
                </span>
                <h3>{t(`landing.features.${key}.title`)}</h3>
                <p>{t(`landing.features.${key}.text`)}</p>
              </article>
            ))}
          </div>
        </section>

        <div className="landing-section">
          <AppDownload showWhenEmpty />
        </div>

        <section className="landing-section" aria-labelledby="landing-steps">
          <h2 id="landing-steps">{t('landing.stepsTitle')}</h2>
          <ol className="landing-steps">
            {STEPS.map((key, i) => (
              <li key={key} className="panel">
                <span className="landing-step__n">{i + 1}</span>
                <h3>{t(`landing.steps.${key}.title`)}</h3>
                <p>{t(`landing.steps.${key}.text`)}</p>
              </li>
            ))}
          </ol>
        </section>

        <section className="landing-section" aria-labelledby="landing-safety">
          <h2 id="landing-safety">{t('landing.safetyTitle')}</h2>
          <p className="landing-lead">{t('landing.safetyText')}</p>
          <ul className="landing-list">
            {SAFETY.map((key) => (
              <li key={key}>
                <Icon name="check" size={18} />
                <span>{t(`landing.safety.${key}`)}</span>
              </li>
            ))}
          </ul>
        </section>

        <section className="landing-final">
          <h2>{t('landing.finalTitle')}</h2>
          <Link to="/register" className="ms-btn ms-btn--primary ms-btn--l">
            {t('landing.start')}
          </Link>
          <p>{t('landing.finalHint')}</p>
        </section>
      </main>

      <footer className="landing-footer">
        <span>MusicStudio</span>
        <Link to="/login">{t('auth.login')}</Link>
      </footer>
    </div>
  )
}
