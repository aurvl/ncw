import { motion } from 'motion/react'
import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import type { Dataset } from '../lib/data'
import { hectares, money, pct, tonnes } from '../lib/format'
import type { Lang } from '../lib/types'

type Props = { data: Dataset; kind: 'regions' | 'groups'; name: string; onClose: () => void }

type Item = { label: string; field: string; fmt: 'money' | 'tco2Yr' | 'tco2' | 'ha' | 'pct' | 'count'; counted?: boolean }

// Totals are sums of unit means, as in the paper's region and group tables.
const SECTIONS: { key: string; tone: string; items: Item[] }[] = [
  { key: 'summary', tone: 'ncw', items: [
    { label: 'ncw', field: 'ncw_usd2015_yr', fmt: 'money', counted: true },
    { label: 'shareWorld', field: 'share_world_ncw_pct', fmt: 'pct' },
    { label: 'gcw', field: 'gcw_usd2015_yr', fmt: 'money', counted: true },
    { label: 'bcw', field: 'bcw_usd2015_yr', fmt: 'money', counted: true },
    { label: 'unitsBoth', field: 'units_both', fmt: 'count' },
  ] },
  { key: 'forest', tone: 'green', items: [
    { label: 'forestAdditions', field: 'forest_additions_tco2_yr', fmt: 'tco2Yr', counted: true },
    { label: 'forestArea', field: 'forest_area_2025_ha', fmt: 'ha', counted: true },
  ] },
  { key: 'blue', tone: 'blue', items: [
    { label: 'mangroveArea', field: 'mangrove_area_gmw_2025_ha', fmt: 'ha', counted: true },
  ] },
  { key: 'economy', tone: 'neutral', items: [
    { label: 'medianGcwGdp', field: 'median_gcw_gdp_2024_pct', fmt: 'pct' },
  ] },
  { key: 'climate', tone: 'purple', items: [
    { label: 'emissions', field: 'emissions_tco2_2024', fmt: 'tco2', counted: true },
  ] },
  { key: 'deforestation', tone: 'erosion', items: [
    { label: 'capacityLoss', field: 'capacity_loss_tco2_yr', fmt: 'tco2Yr', counted: true },
  ] },
  { key: 'finance', tone: 'amber', items: [
    { label: 'ourAllocation', field: 'our_2pct_gcw_allocation_usd2015_yr', fmt: 'money', counted: true },
  ] },
]

export default function AggregatePanel({ data, kind, name, onClose }: Props) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language as Lang
  const profile = data.aggregates[kind].find((p) => p.key === name)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])
  if (!profile) return null

  const perYear = lang === 'fr' ? ' / an' : ' / yr'
  const format = (v: number, fmt: Item['fmt']) => {
    switch (fmt) {
      case 'money': return money(v, lang) + perYear
      case 'tco2Yr': return tonnes(v, lang, 'CO2') + perYear
      case 'tco2': return tonnes(v, lang, 'CO2')
      case 'ha': return hectares(v, lang)
      case 'pct': return pct(v, lang)
      case 'count': return String(v)
    }
  }
  const g = (profile.gcw_usd2015_yr as number | null) ?? 0
  const b = (profile.bcw_usd2015_yr as number | null) ?? 0
  const share = g + b > 0 ? (g / (g + b)) * 100 : null
  const label = kind === 'regions' ? t(`regions.${name}`, { defaultValue: name }) : t(`groups.${name}`, { defaultValue: name })

  return (
    <motion.aside className="panel" aria-label={label}
                  initial={{ x: 40, opacity: 0 }} animate={{ x: 0, opacity: 1 }} exit={{ x: 40, opacity: 0 }}
                  transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}>
      <header className="panel-head">
        <div>
          <p className="kicker">{t(kind === 'regions' ? 'aggregate.region' : 'aggregate.group')}</p>
          <h2>{label}</h2>
          <div className="chips"><span className="chip">{t('aggregate.units', { n: profile.units })}</span></div>
        </div>
        <button className="close" onClick={onClose} aria-label={t('panel.close')}>×</button>
      </header>
      <div className="panel-body">
        <p className="muted small">{t('aggregate.note')}</p>
        {SECTIONS.map((s, i) => (
          <motion.section key={s.key} className="panel-section" data-tone={s.tone}
                          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.15 + i * 0.05 }}>
            <h3>{t(`panel.sections.${s.key}`)}</h3>
            {s.key === 'summary' && share !== null && (
              <div className="split" aria-hidden="true">
                <div className="split-bar">
                  <motion.span className="split-green" initial={{ width: 0 }} animate={{ width: `${share}%` }} transition={{ duration: 1, delay: 0.3 }} />
                  <span className="split-blue" />
                </div>
                <div className="split-labels"><span>{t('panel.shareGcw')} {share.toFixed(0)}%</span><span>{t('panel.shareBcw')} {(100 - share).toFixed(0)}%</span></div>
              </div>
            )}
            <dl>
              {s.items.map((it) => {
                const v = profile[it.field]
                const n = profile[`${it.field}_n`]
                return (
                  <div key={it.field} className="row">
                    <dt>{t(`aggregate.fields.${it.label}`)}</dt>
                    <dd>
                      {typeof v === 'number' ? <span className="value">{format(v, it.fmt)}</span> : <span className="nodata">{t('panel.noData')}</span>}
                      {it.counted && typeof n === 'number' && <span className="rank">{t('aggregate.n', { n })}</span>}
                    </dd>
                  </div>
                )
              })}
            </dl>
            {s.key === 'summary' && typeof profile.green_dominant_units === 'number' && (
              <dl>
                {(['green_dominant_units', 'mixed_units', 'blue_dominant_units'] as const).map((f) => (
                  <div key={f} className="row"><dt>{t(`aggregate.fields.${f}`)}</dt><dd><span className="value">{profile[f]}</span></dd></div>
                ))}
              </dl>
            )}
          </motion.section>
        ))}
      </div>
    </motion.aside>
  )
}
