import { useTranslation } from 'react-i18next'
import { type CSSProperties, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { AppDownload } from '../components/AppDownload'
import { LanguageToggle, ThemeToggle } from '../components/Preferences'
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
// Real screens of the portal at phone width, captured once from the portal against the real API.
const GALLERY = ['home', 'student', 'payments', 'parent'] as const

/** A phone drawn in CSS around a real screenshot: no image of a device to license or keep in sync. */
function Phone({ shot, alt }: { shot: string; alt: string }) {
  const { theme } = useTheme()
  return (
    <div className="phone">
      <img src={`/showcase/${shot}-${theme}.jpg`} alt={alt} width={390} height={844} loading="lazy" />
    </div>
  )
}

/**
 * The brand video (rendered from video/ with HyperFrames). It never starts by itself: a cover
 * with a play button ringed by the package "beats" waits for a click. That click is a user
 * gesture, so the browser lets it play with sound, and nothing is downloaded before it.
 * Web copy of the 1080p master (720p looked soft on retina screens):
 *   ffmpeg -i video/musicstudio.mp4 -c:v libx264 -crf 20 -preset slow -tune animation \
 *     -pix_fmt yuv420p -c:a aac -b:a 128k -movflags +faststart frontend/public/showcase/musicstudio.mp4
 */
function VideoTour() {
  const { t } = useTranslation()
  const video = useRef<HTMLVideoElement>(null)
  const [started, setStarted] = useState(false)

  function start() {
    setStarted(true)
    void video.current?.play()
  }

  return (
    <div className="video-tour">
      <video
        ref={video}
        src="/showcase/musicstudio.mp4"
        poster="/showcase/musicstudio-poster.jpg"
        aria-label={t('landing.videoLabel')}
        width={1920}
        height={1080}
        preload="none"
        controls={started}
        playsInline
      />
      {!started && (
        <button type="button" className="video-tour__cover" onClick={start}>
          <span className="video-tour__play" aria-hidden="true">
            {Array.from({ length: 8 }, (_, i) => (
              <i key={i} style={{ '--i': i } as CSSProperties} />
            ))}
          </span>
          <span className="video-tour__label">{t('landing.playVideo')}</span>
        </button>
      )}
    </div>
  )
}

/** What a visitor sees before signing in: what the product is, and how to start. */
export function Landing() {
  const { t } = useTranslation()

  return (
    <div className="landing">
      <header className="landing-bar">
        <Logo size={40} />
        <nav className="landing-bar__tools" aria-label={t('landing.nav')}>
          <a href="#landing-steps" className="landing-bar__link">
            {t('landing.stepsTitle')}
          </a>
          <a href="#landing-gallery" className="landing-bar__link">
            {t('landing.galleryTitle')}
          </a>
          <Link to="/login" className="ms-btn ms-btn--secondary ms-btn--s">
            {t('auth.login')}
          </Link>
          <Link to="/register" className="ms-btn ms-btn--primary ms-btn--s">
            {t('landing.start')}
          </Link>
          <ThemeToggle />
          <LanguageToggle />
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
            <a href="#video" className="landing-hero__video-link">
              ▶ {t('landing.watchVideo')}
            </a>
            <p className="landing-hero__hint">{t('landing.inviteHint')}</p>
          </div>
          <div className="landing-hero__visual">
            <Phone shot="home" alt={t('landing.gallery.home')} />
            <div className="landing-hero__card">
              <span className="ms-label">{t('landing.sampleLabel')}</span>
              <Beats onPlum size="l" total={8} used={3} />
              <span className="landing-hero__number">{t('landing.sampleRemaining')}</span>
            </div>
          </div>
        </section>

        <section className="landing-section" aria-labelledby="landing-video" id="video">
          <h2 id="landing-video">{t('landing.videoTitle')}</h2>
          <p className="landing-lead">{t('landing.videoText')}</p>
          <VideoTour />
        </section>

        <section className="landing-section" aria-labelledby="landing-features">
          <h2 id="landing-features">{t('landing.featuresTitle')}</h2>
          <div className="landing-grid">
            {FEATURES.map(({ key, icon }) => (
              <article key={key} className="panel reveal">
                <span className="landing-icon">
                  <Icon name={icon} size={24} />
                </span>
                <h3>{t(`landing.features.${key}.title`)}</h3>
                <p>{t(`landing.features.${key}.text`)}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="landing-section" aria-labelledby="landing-gallery">
          <h2 id="landing-gallery">{t('landing.galleryTitle')}</h2>
          <p className="landing-lead">{t('landing.galleryText')}</p>
          <ul className="landing-gallery reveal">
            {GALLERY.map((shot) => (
              <li key={shot}>
                <Phone shot={shot} alt={t(`landing.gallery.${shot}`)} />
                <span>{t(`landing.gallery.${shot}`)}</span>
              </li>
            ))}
          </ul>
        </section>

        <div className="landing-section">
          <AppDownload showWhenEmpty />
        </div>

        <section className="landing-section" aria-labelledby="landing-steps">
          <h2 id="landing-steps">{t('landing.stepsTitle')}</h2>
          <ol className="landing-steps">
            {STEPS.map((key, i) => (
              <li key={key} className="panel reveal">
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
          <p>
            {t('landing.haveAccount')} <Link to="/login">{t('auth.login')}</Link>
          </p>
        </section>
      </main>

      <footer className="landing-footer">
        <span>MusicStudio</span>
        <Link to="/login">{t('auth.login')}</Link>
      </footer>
    </div>
  )
}
