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
  busch_scenario_status: string | null
  emissions_2024_match_status: string | null
  mangrove_area_source: string | null
  has_gcw: boolean | null
  has_bcw: boolean | null
  desk_study: boolean | null
  reported_deforestation: boolean | null
  busch_curve_available: boolean | null
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
  features: { type: 'Feature'; properties: { code: string }; geometry: { type: string; coordinates: unknown } }[]
}

export type Lang = 'en' | 'fr'
export type Theme = 'light' | 'dark'
