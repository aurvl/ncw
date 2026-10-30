// One record of public/data/units.json (built by scripts/build_web_data.py).
// Field names are kept identical to the repository's master country table.
export type Unit = {
  UNIT_CODE: string
  name: string | null
  continent: string | null
  region: string | null
  groups: string | null
  sovereign: string | null
  unit_class: string | null
  overlap_status: string | null
  emissions_2024_match_status: string | null
  mangrove_area_source: string | null
  has_gcw: boolean | null
  has_bcw: boolean | null
  desk_study: boolean | null
  reported_deforestation: boolean | null
} & Record<string, number | string | boolean | null>

export type GlobalTotals = {
  gcw: Total
  bcw: Total
  ncw: Total
  counts: { gcw_units: number; ncw_units: number }
}

type Total = { mean_trillion: number; p05_trillion: number; p95_trillion: number; share_pct: number }

// Totals by region or economic group (public/data/aggregates.json). Each sum has a `_n` count of contributing units.
export type AggregateProfile = {
  key: string
  units: number
  units_gcw: number
  units_bcw: number
  units_both: number
  share_world_ncw_pct: number
  median_gcw_gdp_2024_pct?: number | null
  green_dominant_units?: number
  mixed_units?: number
  blue_dominant_units?: number
} & Record<string, number | string | null | undefined>

export type Aggregates = { regions: AggregateProfile[]; groups: AggregateProfile[] }

export type FeatureCollection = {
  type: 'FeatureCollection'
  features: { type: 'Feature'; properties: { code: string; unit?: string }; geometry: { type: string; coordinates: unknown } }[]
}

// BCW source record of Hilmi et al. (public/data/bcw_sources.json). Each record is counted in one
// accounting unit: e.g. Trindade (BR-ES) in Brazil (BRA). EEZ polygons are keyed by record code.
export type BcwSource = { code: string; unit: string; role: 'unit_row' | 'main_part' | 'part'; name: string | null; territory: string | null }

// Forest-restoration soil scenarios shown on the site; the first is the default.
export const SOIL_SCENARIOS = ['busch_reference', 'zero_soil_change'] as const
export type Soil = (typeof SOIL_SCENARIOS)[number]

// public/data/restoration.json: results by unit and soil scenario, and the units with curve files.
export type Restoration = {
  scenarios: Soil[]
  units: Record<string, Partial<Record<Soil, Record<string, number | string>>>>
  curves: string[]
}

// public/data/curves/<ISO3>.json: points are [cumulative discounted 30-year tCO2, US$2015 per tCO2].
export type Curves = Partial<Record<Soil, { price_supply?: [number, number][]; effective_cost?: [number, number][] }>>

export type Lang = 'en' | 'fr'
export type Theme = 'light' | 'dark'
