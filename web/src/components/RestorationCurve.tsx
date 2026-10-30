import { scaleLinear, scaleLog } from 'd3-scale'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { loadCurves } from '../lib/data'
import { plain, tonnes } from '../lib/format'
import type { Curves, Lang, Soil } from '../lib/types'

type Props = { code: string; soil: Soil; target: number | null; marginal: number | null }

const W = 360, H = 210, M = { top: 12, right: 12, bottom: 34, left: 44 }

// Restoration supply for one country: the effective-cost curve (marginal cost of the cheapest cells
// reaching each cumulative quantity) and the price-supply curve (quantity offered at each price),
// both against cumulative discounted 30-year tCO2 on a log axis, with the restoration target.
export default function RestorationCurve({ code, soil, target, marginal }: Props) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language as Lang
  const [curves, setCurves] = useState<Curves | null>(null)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    let live = true
    loadCurves(code).then((c) => live && setCurves(c)).catch(() => live && setFailed(true))
    return () => { live = false }
  }, [code])

  if (failed) return <p className="muted small">{t('restoration.curveError')}</p>
  if (!curves) return <div className="curve-placeholder" aria-hidden="true" />
  const scenario = curves[soil]
  const effective = (scenario?.effective_cost ?? []).filter(([q]) => q > 0)
  const supply = (scenario?.price_supply ?? []).filter(([q]) => q > 0)
  if (!effective.length && !supply.length) return null

  const qs = [...effective, ...supply].map(([q]) => q).concat(target && target > 0 ? [target] : [])
  const x = scaleLog().domain([Math.min(...qs), Math.max(...qs)]).range([M.left, W - M.right]).nice()
  // The last cells of the effective-cost curve can be far above the rest; the axis stops at the
  // price-supply range or the 95th percentile of the effective cost, and higher points are clipped.
  const costs = effective.map(([, p]) => p).sort((a, b) => a - b)
  const p95 = costs.length ? costs[Math.floor(0.95 * (costs.length - 1))] : -Infinity
  const prices = supply.map(([, p]) => p)
  const top = Math.max(p95, ...prices, marginal ?? -Infinity, 0)
  const bottom = Math.min(...costs, ...prices, marginal ?? Infinity, 0)
  const y = scaleLinear().domain([bottom, top]).range([H - M.bottom, M.top]).nice(5)
  const [yLo, yHi] = y.domain()
  const clip = (p: number) => Math.min(Math.max(p, yLo), yHi)

  const effPath = effective.map(([q, p], i) => `${i ? 'L' : 'M'}${x(q).toFixed(1)},${y(clip(p)).toFixed(1)}`).join('')
  // Price supply is a step: the cumulative quantity holds until the next price level.
  const supplyPath = supply.map(([q, p], i) => {
    const px = x(q).toFixed(1), py = y(clip(p)).toFixed(1)
    return i ? `V${py}H${px}` : `M${px},${py}`
  }).join('')
  const xTicks = x.ticks().filter((v) => Math.abs(Math.log10(v) - Math.round(Math.log10(v))) < 1e-9)
  const yTicks = y.ticks(5)

  return (
    <figure className="curve">
      <figcaption className="chart-title">{t('restoration.curveTitle')}</figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t('restoration.curveTitle')}>
        {yTicks.map((v) => (
          <g key={`y${v}`}>
            <line x1={M.left} x2={W - M.right} y1={y(v)} y2={y(v)} className={v === 0 ? 'axis-zero' : 'grid'} />
            <text x={M.left - 6} y={y(v)} className="tick" textAnchor="end" dominantBaseline="middle">{plain(v, lang, 0)}</text>
          </g>
        ))}
        {xTicks.map((v) => (
          <text key={`x${v}`} x={x(v)} y={H - M.bottom + 14} className="tick" textAnchor="middle">{tonnes(v, lang, 'CO2').replace('CO₂', '')}</text>
        ))}
        <text x={(M.left + W - M.right) / 2} y={H - 4} className="axis-label" textAnchor="middle">{t('restoration.axisX')}</text>
        <text transform={`translate(11 ${(M.top + H - M.bottom) / 2}) rotate(-90)`} className="axis-label" textAnchor="middle">{t('restoration.axisY')}</text>
        {supplyPath && <path d={supplyPath} className="curve-supply" />}
        {effPath && <path d={effPath} className="curve-effective" />}
        {target !== null && target > 0 && (
          <g>
            <line x1={x(target)} x2={x(target)} y1={M.top} y2={H - M.bottom} className="curve-target" />
            <text x={x(target) + 4} y={M.top + 8} className="tick">{t('restoration.target')}</text>
            {marginal !== null && <circle cx={x(target)} cy={y(clip(marginal))} r={3.5} className="curve-marginal" />}
          </g>
        )}
      </svg>
      <div className="curve-legend">
        <span><i className="line effective" />{t('restoration.effective')}</span>
        <span><i className="line supply" />{t('restoration.supply')}</span>
        {target !== null && target > 0 && <span><i className="line target" />{t('restoration.targetLegend')}</span>}
      </div>
    </figure>
  )
}
