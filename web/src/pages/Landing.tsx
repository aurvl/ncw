import { motion } from 'motion/react'
import { useTranslation } from 'react-i18next'
import type { GlobalTotals, Lang } from '../lib/types'
import { money, range } from '../lib/format'

const rise = (delay: number) => ({
  initial: { opacity: 0, y: 14 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.9, delay, ease: [0.22, 1, 0.36, 1] as const },
})

export default function Landing({ global, onExplore }: { global: GlobalTotals; onExplore: () => void }) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language as Lang
  const stats = [
    { key: 'ncw', label: 'NCW', total: global.ncw, tone: 'ncw' },
    { key: 'gcw', label: 'GCW', total: global.gcw, tone: 'green' },
    { key: 'bcw', label: 'BCW', total: global.bcw, tone: 'blue' },
  ]
  return (
    <motion.section className="landing" exit={{ opacity: 0, transition: { duration: 0.6 } }}>
      <div className="landing-inner">
        <motion.h1 {...rise(0.25)}>{t('app.title')}</motion.h1>
        <motion.p className="authors" {...rise(0.4)}>{t('app.authors')}</motion.p>
        <motion.p className="lede" {...rise(0.55)}>{t('landing.lede')}</motion.p>
        <motion.div className="landing-actions" {...rise(0.7)}>
          <button className="cta" onClick={onExplore}>
            {t('landing.cta')}
            <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
          </button>
        </motion.div>
        <motion.dl className="landing-stats" {...rise(0.9)}>
          {stats.map((s) => (
            <div key={s.key} className={`stat tone-${s.tone}`}>
              <dt>{s.label}</dt>
              <dd>{money(s.total.mean_trillion * 1e12, lang)}</dd>
              <dd className="stat-range">{range(s.total.mean_trillion * 1e12, s.total.p05_trillion * 1e12, s.total.p95_trillion * 1e12, lang, 'money')}</dd>
            </div>
          ))}
          <p className="stat-note">{t('landing.stats')}</p>
        </motion.dl>
      </div>
    </motion.section>
  )
}
