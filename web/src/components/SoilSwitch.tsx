import { useTranslation } from 'react-i18next'
import { SOIL_SCENARIOS, type Soil } from '../lib/types'

// Forest-restoration soil scenario: soil carbon gains of the reference method, or none.
export default function SoilSwitch({ soil, onChange }: { soil: Soil; onChange: (s: Soil) => void }) {
  const { t } = useTranslation()
  return (
    <div className="soil-switch" role="radiogroup" aria-label={t('soil.label')}>
      <span className="soil-label">{t('soil.label')}</span>
      <div className="segmented">
        {SOIL_SCENARIOS.map((s) => (
          <button key={s} type="button" role="radio" aria-checked={s === soil} className={s === soil ? 'active' : ''}
                  title={t(`soil.hint.${s}`)} onClick={() => onChange(s)}>
            {t(`soil.${s}`)}
          </button>
        ))}
      </div>
    </div>
  )
}
