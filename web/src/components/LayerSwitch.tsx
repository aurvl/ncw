import { AnimatePresence, motion } from 'motion/react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { LAYERS, MAIN_LAYERS, MORE_LAYERS, swatchColor, type LayerKey } from '../lib/layers'

export default function LayerSwitch({ layer, onChange }: { layer: LayerKey; onChange: (l: LayerKey) => void }) {
  const { t } = useTranslation()
  const inMore = !MAIN_LAYERS.includes(layer)
  const [open, setOpen] = useState(inMore)

  const option = (key: LayerKey) => (
    <label key={key} className={key === layer ? 'active' : ''}>
      <input type="radio" name="layer" value={key} checked={key === layer} onChange={() => onChange(key)} />
      <span className="swatch" style={{ background: swatchColor(LAYERS[key]) }} />
      {t(`layers.${key}`)}
    </label>
  )

  return (
    <>
      <fieldset className="card layer-switch">
        <legend>{t('explorer.layer')}</legend>
        {MAIN_LAYERS.map(option)}
        <button type="button" className={`more-toggle ${open ? 'open' : ''}`} aria-expanded={open} onClick={() => setOpen(!open)}>
          {t(open ? 'explorer.fewerLayers' : 'explorer.moreLayers')}
          <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
        </button>
        <AnimatePresence initial={false}>
          {open && (
            <motion.div className="more-layers" initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}>
              {MORE_LAYERS.map((g) => (
                <div key={g.group} className="layer-group">
                  <p className="layer-group-title">{t(`layerGroups.${g.group}`)}</p>
                  {g.layers.map(option)}
                </div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </fieldset>

      {/* Small screens: one native select with grouped options. */}
      <label className="card layer-select">
        <span className="sr-only">{t('explorer.layer')}</span>
        <select value={layer} onChange={(e) => onChange(e.target.value as LayerKey)}>
          <optgroup label={t('explorer.layer')}>
            {MAIN_LAYERS.map((k) => <option key={k} value={k}>{t(`layers.${k}`)}</option>)}
          </optgroup>
          {MORE_LAYERS.map((g) => (
            <optgroup key={g.group} label={t(`layerGroups.${g.group}`)}>
              {g.layers.map((k) => <option key={k} value={k}>{t(`layers.${k}`)}</option>)}
            </optgroup>
          ))}
        </select>
      </label>
    </>
  )
}
