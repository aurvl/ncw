import { useTranslation } from 'react-i18next'
import type { Dataset } from '../lib/data'
import { breakLabels, LAYERS, type LayerKey } from '../lib/layers'

// One continuous bar with labels at class breaks, then status boxes of the same size,
// mirroring the legend of the paper's GCW/BCW map. Category layers list their classes.
export default function Legend({ layer, data }: { layer: LayerKey; data: Dataset }) {
  const { t, i18n } = useTranslation()
  const def = LAYERS[layer]
  const hasZeros = def.kind === 'classes' && data.list.some((u) => def.isZero(u))
  return (
    <div className="card legend" aria-label={t(`layers.${layer}`)}>
      <p className="legend-title">{t(`layers.${layer}`)} <span>({t(def.unitKey)})</span></p>
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
          <span><i className="legend-box missing" />{t('legend.noData')}</span>
          {hasZeros && <span><i className="legend-box zero" />{t('legend.zero')}</span>}
        </div>
      </div>
    </div>
  )
}
