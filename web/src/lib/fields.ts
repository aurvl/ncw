// Country-panel layout: which master-table fields appear in which section and how
// they are formatted. Values are displayed as stored; only units are scaled.

export type Fmt = 'moneyYr' | 'money' | 'moneyPerCapita' | 'tco2Yr' | 'tco2' | 'tcYr' | 'ha' | 'km2' | 'pct' | 'fraction'
  | 'ratio' | 'people' | 'bool' | 'status'

export type Field = { key: string; fmt: Fmt; p05?: string; p95?: string; rank?: 'ncw' | 'gcw' | 'bcw' }

export type Section = { key: string; tone: string; fields: Field[]; chart?: 'wealthSplit' | 'biomes' | 'blueEcosystems' }

export const SECTIONS: Section[] = [
  {
    key: 'summary', tone: 'ncw', chart: 'wealthSplit',
    fields: [
      { key: 'ncw_usd2015_yr_mean', fmt: 'moneyYr', p05: 'ncw_usd2015_yr_p05', p95: 'ncw_usd2015_yr_p95', rank: 'ncw' },
      { key: 'gcw_usd2015_yr_mean', fmt: 'moneyYr', p05: 'gcw_usd2015_yr_p05', p95: 'gcw_usd2015_yr_p95', rank: 'gcw' },
      { key: 'bcw_usd2015_yr_mean', fmt: 'moneyYr', p05: 'bcw_usd2015_yr_p05', p95: 'bcw_usd2015_yr_p95', rank: 'bcw' },
      { key: 'forest_share_of_ncw', fmt: 'fraction' },
      { key: 'gcw_share_global_pct', fmt: 'pct' },
    ],
  },
  {
    key: 'forest', tone: 'green', chart: 'biomes',
    fields: [
      { key: 'uptake_tco2_yr_mean', fmt: 'tco2Yr', p05: 'uptake_tco2_yr_p05', p95: 'uptake_tco2_yr_p95' },
      { key: 'fra_total_forest_area_2025_ha', fmt: 'ha' },
      { key: 'fra_primary_forest_2025_ha', fmt: 'ha' },
      { key: 'fra_planted_forest_2025_ha', fmt: 'ha' },
      { key: 'fra_other_wooded_land_2025_ha', fmt: 'ha' },
      { key: 'fra_mangroves_2025_ha', fmt: 'ha' },
      { key: 'documented_forest_mangrove_area_ha', fmt: 'ha' },
      { key: 'overlap_status', fmt: 'status' },
    ],
  },
  {
    key: 'blue', tone: 'blue', chart: 'blueEcosystems',
    fields: [
      { key: 'mangrove_area_selected_ha', fmt: 'ha' },
      { key: 'mangrove_area_source', fmt: 'status' },
      { key: 'selected_mangrove_uptake_tCO2_yr_mean', fmt: 'tco2Yr' },
      { key: 'saltmarsh_area_km2_hilmi_source', fmt: 'km2' },
      { key: 'saltmarsh_uptake_tC_yr_source_mean', fmt: 'tcYr' },
      { key: 'seagrass_area_km2_hilmi_source', fmt: 'km2' },
      { key: 'seagrass_uptake_tC_yr_source_mean', fmt: 'tcYr' },
      { key: 'coastal_component_uptake_tCO2_yr_current_area', fmt: 'tco2Yr' },
      { key: 'open_ocean_bcp_tCO2_yr_source', fmt: 'tco2Yr' },
      { key: 'bcw_source_eez_area_km2', fmt: 'km2' },
    ],
  },
  {
    key: 'economy', tone: 'neutral',
    fields: [
      { key: 'population_2024', fmt: 'people' },
      { key: 'gdp_2015usd_2024', fmt: 'money' },
      { key: 'gdp_per_capita_2024', fmt: 'moneyPerCapita' },
      { key: 'gcw_gdp_2024_pct', fmt: 'pct' },
      { key: 'bcw_gdp_2024_pct', fmt: 'pct' },
    ],
  },
  {
    key: 'climate', tone: 'purple',
    fields: [
      { key: 'co2_emissions_tco2_2024', fmt: 'tco2' },
      { key: 'gcw_additions_to_emissions_ratio', fmt: 'ratio' },
      { key: 'gcw_accounting_balance_mean_tco2_yr', fmt: 'tco2Yr' },
      { key: 'ncw_accounting_balance_mean_tco2_yr', fmt: 'tco2Yr' },
    ],
  },
  {
    key: 'deforestation', tone: 'erosion',
    fields: [
      { key: 'reported_deforestation', fmt: 'bool' },
      { key: 'loss_tco2_mean', fmt: 'tco2Yr' },
      { key: 'loss_value_usd2015_yr_mean', fmt: 'moneyYr' },
      { key: 'erosion_pct_of_gcw', fmt: 'pct' },
      { key: 'loss_pct_of_gdp', fmt: 'pct' },
    ],
  },
  {
    key: 'finance', tone: 'amber',
    fields: [
      { key: 'our_2pct_gcw_allocation_usd2015_yr', fmt: 'moneyYr' },
      { key: 'busch_scenario_status', fmt: 'status' },
    ],
  },
  {
    key: 'quality', tone: 'muted',
    fields: [
      { key: 'has_gcw', fmt: 'bool' },
      { key: 'has_bcw', fmt: 'bool' },
      { key: 'desk_study', fmt: 'bool' },
      { key: 'emissions_2024_match_status', fmt: 'status' },
      { key: 'unit_class', fmt: 'status' },
    ],
  },
]

export { BIOME_COLORS, BIOMES } from './layers'
