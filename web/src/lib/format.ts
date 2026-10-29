import type { Lang } from './types'

// Formatting only: values are never recalculated, only scaled for display.

const nf = (lang: Lang, digits: number) =>
  new Intl.NumberFormat(lang === 'fr' ? 'fr-FR' : 'en-US', { maximumFractionDigits: digits, minimumFractionDigits: 0 })

function sig(value: number) {
  const a = Math.abs(value)
  return a >= 100 ? 0 : a >= 10 ? 1 : 2
}

function scaled(value: number, lang: Lang, steps: [number, string][]) {
  for (const [size, suffix] of steps) {
    if (Math.abs(value) >= size) return `${nf(lang, sig(value / size)).format(value / size)}${suffix}`
  }
  return nf(lang, sig(value)).format(value)
}

// US$: French uses "Md" (milliard) to avoid the billion/trillion ambiguity.
const MONEY_STEPS: Record<Lang, number[]> = { en: [1e12, 1e9, 1e6, 1e3], fr: [1e9, 1e6, 1e3] }
const TONNE_STEPS = [1e9, 1e6, 1e3]

export function money(value: number, lang: Lang) {
  if (lang === 'fr') {
    return scaled(value, lang, [[1e9, ' Md'], [1e6, ' M'], [1e3, ' k']]) + ' US$'
  }
  return 'US$ ' + scaled(value, lang, [[1e12, ' tn'], [1e9, ' bn'], [1e6, ' M'], [1e3, ' k']])
}

export function tonnes(value: number, lang: Lang, gas: 'CO2' | 'C') {
  const unit = gas === 'CO2' ? 'CO₂' : 'C'
  return scaled(value, lang, [[1e9, ` Gt${unit}`], [1e6, ` Mt${unit}`], [1e3, ` kt${unit}`]]) +
    (Math.abs(value) < 1e3 ? ` t${unit}` : '')
}

// P05–P95 interval as "[lo – hi]" without units, in the unit already shown for the mean
// (e.g. mean "US$ 969 bn / yr" gives "[379 – 1,757]").
export function range(mean: number, lo: number, hi: number, lang: Lang, kind: 'money' | 'tonnes') {
  const steps = kind === 'money' ? MONEY_STEPS[lang] : TONNE_STEPS
  const size = steps.find((s) => Math.abs(mean) >= s) ?? 1
  const f = (v: number) => nf(lang, sig(v / size)).format(v / size)
  return `[${f(lo)} – ${f(hi)}]`
}

export function hectares(value: number, lang: Lang) {
  return scaled(value, lang, [[1e6, ' Mha'], [1e3, ' kha']]) + (Math.abs(value) < 1e3 ? ' ha' : '')
}

export function km2(value: number, lang: Lang) {
  return `${nf(lang, value >= 100 ? 0 : 1).format(value)} km²`
}

export function count(value: number, lang: Lang) {
  return scaled(value, lang, lang === 'fr' ? [[1e9, ' Md'], [1e6, ' M']] : [[1e9, ' bn'], [1e6, ' M']])
}

export function pct(value: number, lang: Lang) {
  const a = Math.abs(value)
  const digits = a === 0 ? 0 : a < 0.01 ? 4 : a < 1 ? 3 : a < 10 ? 2 : 1
  return nf(lang, digits).format(value) + (lang === 'fr' ? ' %' : '%')
}

export function plain(value: number, lang: Lang, digits = 3) {
  return nf(lang, digits).format(value)
}
