import { motion } from 'motion/react'
import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { sourceLabel, type Dataset } from '../lib/data'
import { BIOME_COLORS, BIOMES, restorationFields, SECTIONS, type Field } from '../lib/fields'
import { count, hectares, km2, money, pct, plain, range, tonnes } from '../lib/format'
import type { Lang, Soil, Unit } from '../lib/types'
import RestorationCurve from './RestorationCurve'
import SoilSwitch from './SoilSwitch'

type Props = { data: Dataset; code: string; soil: Soil; onSoil: (s: Soil) => void; onClose: () => void }

function useFormat() {
  const { t, i18n } = useTranslation()
  const lang = i18n.language as Lang
  const perYear = lang === 'fr' ? ' / an' : ' / yr'
  return (field: Field, v: number | string | boolean | null): string | null => {
    if (v === null || v === undefined) return null
    switch (field.fmt) {
      case 'bool': return v ? t('panel.yes') : t('panel.no')
      case 'status': return t(`status.${v}`, { defaultValue: String(v) })
    }
    if (typeof v !== 'number') return String(v)
    switch (field.fmt) {
      case 'moneyYr': return money(v, lang) + perYear
      case 'money': return money(v, lang)
      case 'moneyPerT': return money(v, lang) + ' / tCO₂'
      case 'tcHaYr': return t('panel.rate', { rate: plain(v, lang, 3) })
      case 'moneyPerCapita': return money(v, lang)
      case 'tco2Yr': return tonnes(v, lang, 'CO2') + perYear
      case 'tco2': return tonnes(v, lang, 'CO2')
      case 'tcYr': return tonnes(v, lang, 'C') + perYear
      case 'ha': return hectares(v, lang)
      case 'km2': return km2(v, lang)
      case 'pct': return pct(v, lang)
      case 'fraction': return pct(v * 100, lang)
      case 'ratio': return `${plain(v, lang, v < 1 ? 3 : 2)} ×`
      case 'people': return count(v, lang)
    }
    return String(v)
  }
}

function Row({ unit, field, data }: { unit: Unit; field: Field; data: Dataset }) {
  const { t, i18n } = useTranslation()
  const format = useFormat()
  const value = format(field, unit[field.key] as never)
  const mean = unit[field.key], lo = field.p05 && unit[field.p05], hi = field.p95 && unit[field.p95]
  // The panel note already says ranges are P05–P95 and the mean carries the unit, so the
  // interval is shown bare and in the mean's unit.
  const interval = typeof mean === 'number' && typeof lo === 'number' && typeof hi === 'number' && lo !== hi
    ? range(mean, lo, hi, i18n.language as Lang, field.fmt === 'moneyYr' || field.fmt === 'money' ? 'money' : 'tonnes')
    : null
  const rank = field.rank ? data.ranks[field.rank][unit.UNIT_CODE] : undefined
  return (
    <div className="row">
      <dt>{t(`panel.fields.${field.label ?? field.key}`)}</dt>
      <dd>
        {value === null ? <span className="nodata">{t('panel.noData')}</span> : <span className="value">{value}</span>}
        {value !== null && interval && <span className="range">{interval}</span>}
        {rank && <span className="rank">{t('panel.rank', rank)}</span>}
      </dd>
    </div>
  )
}

function WealthSplit({ unit }: { unit: Unit }) {
  const { t } = useTranslation()
  const g = unit.gcw_usd2015_yr_mean as number | null
  const b = unit.bcw_usd2015_yr_mean as number | null
  if (typeof g !== 'number' || typeof b !== 'number' || g + b <= 0) return null
  const share = (g / (g + b)) * 100
  return (
    <div className="split" aria-hidden="true">
      <div className="split-bar">
        <motion.span className="split-green" initial={{ width: 0 }} animate={{ width: `${share}%` }} transition={{ duration: 1, delay: 0.3 }} />
        <span className="split-blue" />
      </div>
      <div className="split-labels"><span>{t('panel.shareGcw')} {share.toFixed(0)}%</span><span>{t('panel.shareBcw')} {(100 - share).toFixed(0)}%</span></div>
    </div>
  )
}

type Part = { key: string; label: string; color: string; value: number; value_text: string; note?: string }

// Stacked bar plus legend list: share of each part in the total shown.
function Composition({ title, parts }: { title: string; parts: Part[] }) {
  const shown = parts.filter((p) => p.value > 0)
  const total = shown.reduce((s, p) => s + p.value, 0)
  if (total <= 0) return null
  return (
    <div className="composition">
      <p className="chart-title">{title}</p>
      <div className="stack">
        {shown.map((p, i) => (
          <motion.span key={p.key} style={{ background: p.color }} title={p.label}
                       initial={{ width: 0 }} animate={{ width: `${(p.value / total) * 100}%` }} transition={{ duration: 0.9, delay: 0.3 + i * 0.08 }} />
        ))}
      </div>
      <ul className="composition-list">
        {shown.map((p) => (
          <li key={p.key}>
            <i style={{ background: p.color }} />
            <span>{p.label}</span>
            <span className="num">{p.value_text}</span>
            <span className="num muted">{p.note ?? `${((p.value / total) * 100).toFixed(0)}%`}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function Biomes({ unit }: { unit: Unit }) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language as Lang
  const parts = BIOMES.map((b) => {
    const area = (unit[`forest_area_allocated_${b}_ha`] as number | null) ?? 0
    const rate = unit[`forest_rate_${b}_tC_ha_yr`] as number | null
    return { key: b, label: t(`panel.biomes.${b}`), color: BIOME_COLORS[b], value: area, value_text: hectares(area, lang),
      note: rate !== null ? t('panel.rate', { rate: plain(rate, lang, 2) }) : '' }
  })
  return <Composition title={t('panel.biomeSplit')} parts={parts} />
}

// Blue account by ecosystem. Saltmarsh and seagrass burial are stored in tC and converted with
// 44/12; the three coastal parts then sum exactly to the stored coastal total, and BCW is valued
// at the same price per tCO2 for every part, so these are also shares of the unit's BCW.
const CO2_PER_C = 44 / 12
const BLUE_PARTS = [
  { key: 'mangrove', field: 'selected_mangrove_uptake_tCO2_yr_mean', factor: 1, color: '#0C7C59' },
  { key: 'seagrass', field: 'seagrass_uptake_tC_yr_source_mean', factor: CO2_PER_C, color: '#5AB4AC' },
  { key: 'saltmarsh', field: 'saltmarsh_uptake_tC_yr_source_mean', factor: CO2_PER_C, color: '#B8CE7A' },
  { key: 'bcp', field: 'open_ocean_bcp_tCO2_yr_source', factor: 1, color: '#1F4E8C' },
]

function BlueEcosystems({ unit }: { unit: Unit }) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language as Lang
  const perYear = lang === 'fr' ? ' / an' : ' / yr'
  const parts = BLUE_PARTS.map((b) => {
    const value = ((unit[b.field] as number | null) ?? 0) * b.factor
    return { key: b.key, label: t(`panel.blueParts.${b.key}`), color: b.color, value, value_text: tonnes(value, lang, 'CO2') + perYear }
  })
  return <Composition title={t('panel.blueSplit')} parts={parts} />
}

// BCW source records counted in this unit when there is more than one (e.g. Brazil and Trindade).
function BcwSources({ data, code }: { data: Dataset; code: string }) {
  const { t } = useTranslation()
  const codes = data.eezByUnit[code] ?? []
  if (codes.length < 2) return null
  // The unit's own or main record first, then its parts.
  const order = (c: string) => (data.sources[c]?.role === 'part' ? 1 : 0)
  const names = [...codes].sort((a, b) => order(a) - order(b)).map((c) => sourceLabel(data, c))
  return <p className="muted small">{t('panel.bcwSources', { names: names.join(', ') })}</p>
}

// Forest restoration for the chosen soil scenario: target, supply, costs and curves.
function RestorationSection({ data, unit, soil, onSoil }: { data: Dataset; unit: Unit; soil: Soil; onSoil: (s: Soil) => void }) {
  const { t } = useTranslation()
  const status = unit[`restoration_status@${soil}`]
  const hasCurve = data.restoration.curves.includes(unit.UNIT_CODE)
  const num = (k: string) => (typeof unit[`${k}@${soil}`] === 'number' ? (unit[`${k}@${soil}`] as number) : null)
  return (
    <>
      <SoilSwitch soil={soil} onChange={onSoil} />
      {status
        ? <dl>{restorationFields(soil).map((f) => <Row key={f.key} unit={unit} field={f} data={data} />)}</dl>
        : <p className="muted small">{t('status.no_restoration_target')}</p>}
      {hasCurve && (
        <RestorationCurve code={unit.UNIT_CODE} soil={soil} target={num('restoration_target_discounted_30yr_tco2')}
                          marginal={num('restoration_marginal_cost_usd2015_tco2')} />
      )}
    </>
  )
}

export default function CountryPanel({ data, code, soil, onSoil, onClose }: Props) {
  const { t } = useTranslation()
  const unit = data.units[code]
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const chips = [unit.region && t(`regions.${unit.region}`, { defaultValue: unit.region }),
    unit.groups && t(`groups.${unit.groups}`, { defaultValue: unit.groups })].filter(Boolean) as string[]

  return (
    <motion.aside className="panel" aria-label={unit.name ?? code}
                  initial={{ x: 40, opacity: 0 }} animate={{ x: 0, opacity: 1 }} exit={{ x: 40, opacity: 0 }}
                  transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}>
      <header className="panel-head">
        <div>
          <p className="kicker">{unit.UNIT_CODE}</p>
          <h2>{unit.name ?? code}</h2>
          {unit.sovereign && unit.sovereign !== unit.name && <p className="muted small">{t('panel.sovereign')}: {unit.sovereign}</p>}
          <div className="chips">{chips.map((c) => <span key={c} className="chip">{c}</span>)}</div>
        </div>
        <button className="close" onClick={onClose} aria-label={t('panel.close')}>×</button>
      </header>
      <div className="panel-body">
        <p className="muted small">{t('panel.valuesNote')}</p>
        {[...SECTIONS.slice(0, -2), { key: 'restoration', tone: 'restoration', fields: [] }, ...SECTIONS.slice(-2)].map((s, i) => (
          <motion.section key={s.key} className="panel-section" data-tone={s.tone}
                          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.15 + i * 0.05 }}>
            <h3>{t(`panel.sections.${s.key}`)}</h3>
            {s.chart === 'wealthSplit' && <WealthSplit unit={unit} />}
            {s.key === 'blue' && <BcwSources data={data} code={code} />}
            {s.key === 'restoration'
              ? <RestorationSection data={data} unit={unit} soil={soil} onSoil={onSoil} />
              : <dl>{s.fields.map((f) => <Row key={f.key} unit={unit} field={f} data={data} />)}</dl>}
            {s.chart === 'biomes' && <Biomes unit={unit} />}
            {s.chart === 'blueEcosystems' && <BlueEcosystems unit={unit} />}
          </motion.section>
        ))}
      </div>
    </motion.aside>
  )
}
