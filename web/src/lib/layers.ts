import type { Soil, Unit } from './types'

// Map layers. Bounds and palettes reuse the paper figures (notebook 08) where one exists:
// GCW/BCW classes from the land/EEZ illustration, GCW/GDP from Figure 1, erosion from
// Figure 3. A value is coloured only when it is available; reported zeros are hatched
// and missing values stay grey.

export type LayerKey =
  | 'ncw' | 'gcw' | 'bcw' | 'gcw_gdp' | 'bcw_gdp' | 'erosion'
  | 'forest_additions' | 'forest_area' | 'biome'
  | 'mangrove_area' | 'seagrass_area' | 'saltmarsh_area' | 'coastal_uptake' | 'ocean_bcp'
  | 'emissions' | 'additions_ratio'
  | 'restoration'
  | 'by_region' | 'by_group'

export type ValueFormat = 'money' | 'pct' | 'tco2Yr' | 'ha' | 'km2' | 'ratio' | 'tco2' | 'moneyPerT'

type Common = {
  key: LayerKey
  target: 'land' | 'eez'
  unitKey: string           // i18n key of the legend unit
}

export type ClassLayer = Common & {
  kind: 'classes'
  field: string
  breaks: number[]          // internal class breaks, in display units
  scale: number             // raw value / scale = display units
  colors: string[]          // breaks.length + 1 colours
  format: ValueFormat       // tooltip formatting of the raw value
  isZero: (u: Unit) => boolean
  signed?: boolean          // negative values are coloured too (otherwise only values > 0)
  statusField?: string      // shown in the tooltip when the unit has no value
  special?: { labelKey: string; color: string; test: (u: Unit) => boolean }  // status coloured apart from the scale
}

export type CategoryLayer = Common & {
  kind: 'categories'
  // Aggregate layers: a click opens the totals of the clicked unit's category.
  aggregate?: 'regions' | 'groups'
  categories: { value: string; color: string; labelKey: string }[]
  category: (u: Unit) => string | null
}

export type LayerDef = ClassLayer | CategoryLayer

const GREEN = ['#E5F5E0', '#C7E9C0', '#A1D99B', '#74C476', '#41AB5D', '#238B45', '#005A32', '#002B18']
const BLUE = ['#DEEBF7', '#C6DBEF', '#9ECAE1', '#6BAED6', '#4292C6', '#2171B5', '#08519C', '#031C4F']
const NCW = ['#F1F8E1', '#D5EFC9', '#A8DDB5', '#7BCCC4', '#4EB3D3', '#2B8CBE', '#0868AC', '#0B4F8A']
const FOREST = ['#ffffcc', '#addd8e', '#78c679', '#1E8E43', '#00552f']
const OCEAN = ['#d6ecf5', '#9ecae1', '#4292c6', '#1f6eb4', '#08306b']
const EROSION = ['#fde3c8', '#f7b267', '#e8833a', '#c75146', '#8c2f26']
const GREEN6 = ['#EDF8E9', '#C7E9C0', '#A1D99B', '#74C476', '#31A354', '#006D2C']
const GREEN7 = ['#EDF8E9', '#C7E9C0', '#A1D99B', '#74C476', '#41AB5D', '#238B45', '#005A32']
const TEAL6 = ['#E0F3F0', '#B2E2DA', '#7FCDBB', '#41B6C4', '#1D91C0', '#0C5E8A']
const BLUE6 = ['#EFF3FF', '#C6DBEF', '#9ECAE1', '#6BAED6', '#3182BD', '#08519C']
const BLUE5 = ['#EFF3FF', '#BDD7E7', '#6BAED6', '#3182BD', '#08519C']
const PURPLE6 = ['#F2F0F7', '#DADAEB', '#BCBDDC', '#9E9AC8', '#756BB1', '#54278F']
// Restoration marginal cost: teal below zero (net gain at the target), orange to red above.
const COST7 = ['#01665E', '#35978F', '#80CDC1', '#C7EAE5', '#FDDBC7', '#F4A582', '#B2182B']
// Brown below 1 (emissions exceed forest additions), teal above 1.
const BRBG6 = ['#8C510A', '#D8B365', '#F6E8C3', '#C7EAE5', '#5AB4AC', '#01665E']

const num = (u: Unit, f: string) => (typeof u[f] === 'number' ? (u[f] as number) : null)
const zeroOf = (f: string, guard: (u: Unit) => boolean = () => true) => (u: Unit) => guard(u) && num(u, f) === 0

function classes(def: Omit<ClassLayer, 'kind' | 'isZero'> & { isZero?: ClassLayer['isZero'] }): ClassLayer {
  return { kind: 'classes', isZero: zeroOf(def.field), ...def }
}

export const BIOMES = ['tropical', 'subtropical', 'temperate', 'boreal'] as const
export const BIOME_COLORS: Record<(typeof BIOMES)[number], string> = {
  tropical: '#1E8E43', subtropical: '#A6D96A', temperate: '#4A9C8C', boreal: '#2C5D7C',
}

// Region colours are a neutral qualitative set; group colours match the paper figures.
export const REGION_COLORS: Record<string, string> = {
  Africa: '#D08C3E', Americas: '#4F8F6F', Asia: '#B5523B', Caribbean: '#3E8EBF', Europe: '#7A6FB0', Oceania: '#2A9D8F',
}
export const GROUP_COLORS: Record<string, string> = {
  'Developed economies': '#2CA02C', 'Developing economies': '#FF7F0E', LDCs: '#D62728', SIDS: '#1F77B4',
}

export const LAYERS: Record<LayerKey, LayerDef> = {
  // NCW = GCW + BCW with a missing component counted as zero (see build_web_data.py).
  ncw: classes({ key: 'ncw', field: 'ncw_usd2015_yr_mean', target: 'land', scale: 1e9, unitKey: 'units.bnUsdYr', format: 'money',
    breaks: [0.001, 0.01, 0.1, 1, 10, 100, 1000], colors: NCW }),
  gcw: classes({ key: 'gcw', field: 'gcw_usd2015_yr_mean', target: 'land', scale: 1e9, unitKey: 'units.bnUsdYr', format: 'money',
    breaks: [0.001, 0.01, 0.1, 1, 10, 100, 1000], colors: GREEN, isZero: zeroOf('gcw_usd2015_yr_mean', (u) => !!u.has_gcw) }),
  bcw: classes({ key: 'bcw', field: 'bcw_usd2015_yr_mean', target: 'eez', scale: 1e9, unitKey: 'units.bnUsdYr', format: 'money',
    breaks: [0.0001, 0.001, 0.01, 0.1, 1, 10, 100], colors: BLUE, isZero: zeroOf('bcw_usd2015_yr_mean', (u) => !!u.has_bcw) }),
  gcw_gdp: classes({ key: 'gcw_gdp', field: 'gcw_gdp_2024_pct', target: 'land', scale: 1, unitKey: 'units.pctGdp', format: 'pct',
    breaks: [1, 5, 25, 100], colors: FOREST }),
  bcw_gdp: classes({ key: 'bcw_gdp', field: 'bcw_gdp_2024_pct', target: 'eez', scale: 1, unitKey: 'units.pctGdp', format: 'pct',
    breaks: [1, 5, 25, 100], colors: OCEAN }),
  erosion: classes({ key: 'erosion', field: 'erosion_pct_of_gcw', target: 'land', scale: 1, unitKey: 'units.pctGcw', format: 'pct',
    breaks: [0.1, 0.25, 0.5, 1], colors: EROSION, isZero: zeroOf('erosion_pct_of_gcw', (u) => !!u.reported_deforestation) }),

  forest_additions: classes({ key: 'forest_additions', field: 'uptake_tco2_yr_mean', target: 'land', scale: 1e6, unitKey: 'units.mtco2Yr', format: 'tco2Yr',
    breaks: [0.01, 0.1, 1, 10, 100, 1000], colors: GREEN7 }),
  forest_area: classes({ key: 'forest_area', field: 'fra_total_forest_area_2025_ha', target: 'land', scale: 1e6, unitKey: 'units.mha', format: 'ha',
    breaks: [0.01, 0.1, 1, 10, 100], colors: GREEN6 }),
  biome: {
    kind: 'categories', key: 'biome', target: 'land', unitKey: 'units.biome',
    categories: BIOMES.map((b) => ({ value: b, color: BIOME_COLORS[b], labelKey: `panel.biomes.${b}` })),
    // Biome holding the largest share of the FRA 2025 forest area allocated by biome.
    category: (u) => {
      let best: string | null = null, max = 0
      for (const b of BIOMES) {
        const a = num(u, `forest_area_allocated_${b}_ha`) ?? 0
        if (a > max) { max = a; best = b }
      }
      return best
    },
  },

  mangrove_area: classes({ key: 'mangrove_area', field: 'mangrove_area_selected_ha', target: 'eez', scale: 1e3, unitKey: 'units.kha', format: 'ha',
    breaks: [0.1, 1, 10, 100, 1000], colors: TEAL6 }),
  seagrass_area: classes({ key: 'seagrass_area', field: 'seagrass_area_km2_hilmi_source', target: 'eez', scale: 1, unitKey: 'units.km2', format: 'km2',
    breaks: [1, 10, 100, 1000, 10000], colors: TEAL6 }),
  saltmarsh_area: classes({ key: 'saltmarsh_area', field: 'saltmarsh_area_km2_hilmi_source', target: 'eez', scale: 1, unitKey: 'units.km2', format: 'km2',
    breaks: [0.1, 1, 10, 100, 1000], colors: TEAL6 }),
  coastal_uptake: classes({ key: 'coastal_uptake', field: 'coastal_component_uptake_tCO2_yr_current_area', target: 'eez', scale: 1e3, unitKey: 'units.ktco2Yr', format: 'tco2Yr',
    breaks: [1, 10, 100, 1000, 10000], colors: BLUE6 }),
  ocean_bcp: classes({ key: 'ocean_bcp', field: 'open_ocean_bcp_tCO2_yr_source', target: 'eez', scale: 1e6, unitKey: 'units.mtco2Yr', format: 'tco2Yr',
    breaks: [0.1, 1, 10, 100], colors: BLUE5 }),

  emissions: classes({ key: 'emissions', field: 'co2_emissions_tco2_2024', target: 'land', scale: 1e6, unitKey: 'units.mtco2', format: 'tco2',
    breaks: [0.1, 1, 10, 100, 1000], colors: PURPLE6 }),
  additions_ratio: classes({ key: 'additions_ratio', field: 'gcw_additions_to_emissions_ratio', target: 'land', scale: 1, unitKey: 'units.ratio', format: 'ratio',
    breaks: [0.1, 0.5, 1, 2, 10], colors: BRBG6 }),

  // Marginal cost at the restoration target, for the soil scenario chosen on the site (see resolveLayer).
  restoration: classes({ key: 'restoration', field: 'restoration_marginal_cost_usd2015_tco2', target: 'land', scale: 1,
    unitKey: 'units.usdPerTco2', format: 'moneyPerT', breaks: [-30, -20, -10, 0, 10, 25], colors: COST7, isZero: () => false,
    signed: true }),

  by_region: {
    kind: 'categories', key: 'by_region', target: 'land', unitKey: 'units.region', aggregate: 'regions',
    categories: Object.entries(REGION_COLORS).map(([value, color]) => ({ value, color, labelKey: `regions.${value}` })),
    category: (u) => u.region,
  },
  by_group: {
    kind: 'categories', key: 'by_group', target: 'land', unitKey: 'units.group', aggregate: 'groups',
    categories: Object.entries(GROUP_COLORS).map(([value, color]) => ({ value, color, labelKey: `groups.${value}` })),
    category: (u) => u.groups,
  },
}

export const MAIN_LAYERS: LayerKey[] = ['ncw', 'gcw', 'bcw', 'gcw_gdp', 'bcw_gdp', 'erosion', 'restoration']
export const MORE_LAYERS: { group: string; layers: LayerKey[] }[] = [
  { group: 'forests', layers: ['forest_additions', 'forest_area', 'biome'] },
  { group: 'marine', layers: ['mangrove_area', 'seagrass_area', 'saltmarsh_area', 'coastal_uptake', 'ocean_bcp'] },
  { group: 'climate', layers: ['emissions', 'additions_ratio'] },
  { group: 'aggregates', layers: ['by_region', 'by_group'] },
]

// Restoration values are stored per soil scenario as `<field>@<scenario>` (see data.ts).
export function resolveLayer(key: LayerKey, soil: Soil): LayerDef {
  const def = LAYERS[key]
  if (key !== 'restoration' || def.kind !== 'classes') return def
  const status = `restoration_status@${soil}`
  return {
    ...def,
    field: `${def.field}@${soil}`,
    statusField: status,
    special: { labelKey: 'legend.outsideSupply', color: '#5E3C99', test: (u) => u[status] === 'target_outside_cell_supply' },
  }
}

export function swatchColor(def: LayerDef) {
  return def.kind === 'classes' ? def.colors[def.colors.length - 2] : def.categories[0].color
}

export type Paint = { kind: 'class'; color: string } | { kind: 'zero' } | { kind: 'missing' }

export function paintFor(u: Unit | undefined, layer: LayerDef): Paint {
  if (!u) return { kind: 'missing' }
  if (layer.kind === 'categories') {
    const c = layer.category(u)
    const cat = layer.categories.find((k) => k.value === c)
    return cat ? { kind: 'class', color: cat.color } : { kind: 'missing' }
  }
  if (layer.special?.test(u)) return { kind: 'class', color: layer.special.color }
  if (layer.isZero(u)) return { kind: 'zero' }
  const v = num(u, layer.field)
  if (v !== null && (v > 0 || layer.signed)) {
    const x = v / layer.scale
    let i = 0
    while (i < layer.breaks.length && x > layer.breaks[i]) i++
    return { kind: 'class', color: layer.colors[i] }
  }
  return { kind: 'missing' }
}

const isPowerOfTen = (b: number) => Math.abs(Math.log10(b) - Math.round(Math.log10(b))) < 1e-9

// Sub-unit breaks use powers of ten only when every break is one (as in the paper map);
// mixed scales such as 0.1 / 0.25 / 0.5 stay decimal.
export function breakLabels(breaks: number[], lang: string) {
  const nf = new Intl.NumberFormat(lang === 'fr' ? 'fr-FR' : 'en-US')
  const powers = breaks.every((b) => b > 0 && isPowerOfTen(b))
  return breaks.map((b) => (b < 1 && powers ? `10${toSuperscript(Math.round(Math.log10(b)))}` : nf.format(b)))
}

function toSuperscript(n: number) {
  const map: Record<string, string> = { '-': '⁻', '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹' }
  return String(n).split('').map((c) => map[c] ?? c).join('')
}
