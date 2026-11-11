import { useTranslation } from 'react-i18next'

import { Icon } from './ui'

/**
 * Where to get the phone app. The Android build link is set at build time (VITE_ANDROID_APK_URL);
 * only an https address is ever used as a link. With no link configured the landing says the app
 * is coming and the signed-in pages show nothing (`showWhenEmpty`).
 */
export function AppDownload({ showWhenEmpty = false }: { showWhenEmpty?: boolean }) {
  const { t } = useTranslation()
  const raw = String(import.meta.env.VITE_ANDROID_APK_URL ?? '').trim()
  const url = raw.startsWith('https://') ? raw : ''
  if (!url && !showWhenEmpty) return null

  return (
    <section className="panel panel--accent landing-app" aria-labelledby="app-download-title">
      <h2 id="app-download-title" className="section-title">
        {t('app.title')}
      </h2>
      <p>{t('app.text')}</p>
      {url ? (
        <>
          <a href={url} className="ms-btn ms-btn--primary" rel="noopener noreferrer" target="_blank">
            <Icon name="plus" size={18} />
            {t('app.downloadAndroid')}
          </a>
          <p className="ms-help">{t('app.installHint')}</p>
        </>
      ) : (
        <p className="ms-help">{t('app.comingSoon')}</p>
      )}
      <p className="ms-help">{t('app.iphone')}</p>
    </section>
  )
}
