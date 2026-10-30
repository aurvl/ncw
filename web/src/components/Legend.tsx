import { useTranslation } from 'react-i18next'
import type { Dataset } from '../lib/data'
import { breakLabels, resolveLayer, type LayerKey } from '../lib/layers'
import type { Soil } from '../lib/types'
import SoilSwitch from './SoilSwitch'

// One continuous bar with labels at class breaks, then status boxes of the same size,
// mirroring the legend of the paper's GCW/BCW map. Category layers list their classes.
export default function Legend({ layer, soil, onSoil, data }: { layer: LayerKey; soil: Soil; onSoil: (s: Soil) => void; data: Dataset }) {
  const { t, i18n } = useTranslation()
  const def = resolveLayer(layer, soil)
  const hasZeros = def.kind === 'classes' && data.list.some((u) => def.isZero(u))
  return (
    <div className="card legend" aria-label={t(`layers.${layer}`)}>
      <p className="legend-title">{t(`layers.${layer}`)} <span>({t(def.unitKey)})</span></p>
      {layer === 'restoration' && <SoilSwitch soil={soil} onChange={onSoil} />}
      <div className="legend-row">
        {def.kind === 'classes' ? (
          <div className="legend-bar">
            {def.colors.map((c) => <span key={c} className="legend-box" style={{ background: c }} />)}
            <div className="legend-ticks">
              {breakLabels(def.breaks, i18n.language).map((label, i) => (
                <span key={label} style={{ left: `${((i + 1) / def.colors.length) * 100}%` }}>{label}</span>
              ))}
            </div>
          </div>
        ) : (
          <div className="legend-categories">
            {def.categories.map((c) => <span key={c.value}><i className="legend-box" style={{ background: c.color }} />{t(c.labelKey)}</span>)}
          </div>
        )}
        <div className="legend-status">
          {def.kind === 'classes' && def.special && (
            <span><i className="legend-box" style={{ background: def.special.color }} />{t(def.special.labelKey)}</span>
          )}
          <span><i className="legend-box missing" />{t(layer === 'restoration' ? 'legend.noRestoration' : 'legend.noData')}</span>
          {hasZeros && <span><i className="legend-box zero" />{t('legend.zero')}</span>}
        </div>
      </div>
    </div>
  )
}
