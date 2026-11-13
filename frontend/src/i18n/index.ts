import i18n from 'i18next'
import LanguageDetector from 'i18next-browser-languagedetector'
import { initReactI18next } from 'react-i18next'

import en from './en.json'
import it from './it.json'

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      it: { translation: it },
    },
    fallbackLng: 'en',
    supportedLngs: ['en', 'it'],
    interpolation: { escapeValue: false },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
      lookupLocalStorage: 'musicstudio-language',
    },
  })

// The page language is what search engines and screen readers read: keep <html lang> in step.
const syncLang = (lng: string) => {
  document.documentElement.lang = lng.split('-')[0]
}
syncLang(i18n.language)
i18n.on('languageChanged', syncLang)

export default i18n
