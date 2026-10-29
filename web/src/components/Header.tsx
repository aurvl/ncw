import { useTranslation } from 'react-i18next'
import type { Theme } from '../lib/types'

type Props = {
  theme: Theme
  explore: boolean
  onTheme: () => void
  onHome: () => void
  onExplore: () => void
  onMethods: () => void
}

export default function Header({ theme, explore, onTheme, onHome, onExplore, onMethods }: Props) {
  const { t, i18n } = useTranslation()
  return (
    <header className="header">
      <button className="brand" onClick={onHome}>
        <span className="brand-mark" aria-hidden="true" />
        <span>{t('app.short')}</span>
      </button>
      <nav className="nav">
        <button className={explore ? 'active' : ''} onClick={onExplore}>{t('nav.explore')}</button>
        <button onClick={onMethods}>{t('nav.methods')}</button>
        <span className="nav-sep" aria-hidden="true" />
        <button className="lang" onClick={() => i18n.changeLanguage(i18n.language === 'fr' ? 'en' : 'fr')}
                aria-label={t('nav.lang')} title={t('nav.lang')}>
          {i18n.language === 'fr' ? 'EN' : 'FR'}
        </button>
        <button className="icon" onClick={onTheme} aria-label={t('nav.theme')} title={t('nav.theme')}>
          {theme === 'dark' ? (
            <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><circle cx="12" cy="12" r="4.5" fill="none" stroke="currentColor" strokeWidth="1.6" /><path d="M12 2.5v2.5M12 19v2.5M2.5 12H5M19 12h2.5M5.3 5.3l1.8 1.8M16.9 16.9l1.8 1.8M5.3 18.7l1.8-1.8M16.9 7.1l1.8-1.8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" /></svg>
          ) : (
            <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" /></svg>
          )}
        </button>
      </nav>
    </header>
  )
}
