import { useTranslation } from 'react-i18next'
import { sourceLabel, type Dataset } from '../lib/data'
import { hectares, km2, money, pct, plain, tonnes } from '../lib/format'
import { resolveLayer, type LayerKey, type ValueFormat } from '../lib/layers'
import type { Lang, Soil } from '../lib/types'

function formatValue(v: number, format: ValueFormat, lang: Lang) {
  const perYear = lang === 'fr' ? ' / an' : ' / yr'
  switch (format) {
    case 'money': return money(v, lang) + perYear
    case 'moneyPerT': return money(v, lang) + ' / tCO₂'
    case 'pct': return pct(v, lang)
    case 'tco2Yr': return tonnes(v, lang, 'CO2') + perYear
    case 'tco2': return tonnes(v, lang, 'CO2')
    case 'ha': return hectares(v, lang)
    case 'km2': return km2(v, lang)
    case 'ratio': return `${plain(v, lang, v < 1 ? 3 : 2)} ×`
  }
}

type Hover = { code: string; source?: string; x: number; y: number }

export default function Tooltip({ data, layer, soil, hover }: { data: Dataset; layer: LayerKey; soil: Soil; hover: Hover }) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language as Lang
  const unit = data.units[hover.code]
  const def = resolveLayer(layer, soil)
  let value = t('panel.noData')
  if (unit && def.kind === 'categories') {
    const c = def.categories.find((k) => k.value === def.category(unit))
    if (c) value = t(c.labelKey)
  } else if (unit && def.kind === 'classes') {
    const status = def.statusField ? unit[def.statusField] : null
    if (def.special?.test(unit)) value = t(def.special.labelKey)
    else if (typeof unit[def.field] === 'number') value = formatValue(unit[def.field] as number, def.format, lang)
    else if (def.statusField) value = t(`status.${status ?? 'no_restoration_target'}`, { defaultValue: String(status) })
  }
  // A BCW source record counted in another unit (e.g. Trindade in Brazil) is named with its unit.
  const source = hover.source ? data.sources[hover.source] : undefined
  const part = source && source.role === 'part' ? sourceLabel(data, source.code) : null
  return (
    <div className="tooltip" style={{ left: hover.x + 14, top: hover.y + 14 }}>
      <strong>{part ?? unit?.name ?? hover.code}</strong>
      {part && <span className="muted">{t('explorer.countedIn', { unit: unit?.name ?? hover.code })}</span>}
      <span>{t(`layers.${layer}`)}: {value}</span>
    </div>
  )
}
