import { useTranslation } from 'react-i18next'
import type { Dataset } from '../lib/data'
import { hectares, km2, money, pct, plain, tonnes } from '../lib/format'
import { LAYERS, type LayerKey, type ValueFormat } from '../lib/layers'
import type { Lang } from '../lib/types'

function formatValue(v: number, format: ValueFormat, lang: Lang) {
  const perYear = lang === 'fr' ? ' / an' : ' / yr'
  switch (format) {
    case 'money': return money(v, lang) + perYear
    case 'pct': return pct(v, lang)
    case 'tco2Yr': return tonnes(v, lang, 'CO2') + perYear
    case 'tco2': return tonnes(v, lang, 'CO2')
    case 'ha': return hectares(v, lang)
    case 'km2': return km2(v, lang)
    case 'ratio': return `${plain(v, lang, v < 1 ? 3 : 2)} ×`
  }
}

export default function Tooltip({ data, layer, hover }: { data: Dataset; layer: LayerKey; hover: { code: string; x: number; y: number } }) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language as Lang
  const unit = data.units[hover.code]
  const def = LAYERS[layer]
  let value = t('panel.noData')
  if (unit && def.kind === 'categories') {
    const c = def.categories.find((k) => k.value === def.category(unit))
    if (c) value = t(c.labelKey)
  } else if (unit && def.kind === 'classes' && typeof unit[def.field] === 'number') {
    value = formatValue(unit[def.field] as number, def.format, lang)
  }
  return (
    <div className="tooltip" style={{ left: hover.x + 14, top: hover.y + 14 }}>
      <strong>{unit?.name ?? hover.code}</strong>
      <span>{t(`layers.${layer}`)}: {value}</span>
    </div>
  )
}
