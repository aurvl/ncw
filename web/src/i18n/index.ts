import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import en from './en.json'
import fr from './fr.json'

function initialLang() {
  try {
    const stored = localStorage.getItem('ncw-lang')
    if (stored === 'en' || stored === 'fr') return stored
  } catch { /* storage unavailable: fall back to the browser language */ }
  return navigator.language.toLowerCase().startsWith('fr') ? 'fr' : 'en'
}

i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, fr: { translation: fr } },
  lng: initialLang(),
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
})

document.documentElement.lang = i18n.language
i18n.on('languageChanged', (lng) => {
  document.documentElement.lang = lng
  try { localStorage.setItem('ncw-lang', lng) } catch { /* ignore */ }
})

export default i18n
