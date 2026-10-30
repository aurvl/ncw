import type { Aggregates, BcwSource, Curves, FeatureCollection, GlobalTotals, Restoration, Unit } from './types'

export type Bounds = { center: [number, number]; width: number; height: number }

export type Dataset = {
  units: Record<string, Unit>
  list: Unit[]
  global: GlobalTotals
  aggregates: Aggregates
  land: FeatureCollection
  eez: FeatureCollection
  bounds: Record<string, Bounds>
  // BCW source records, and the EEZ polygons (source codes) drawn for each accounting unit.
  sources: Record<string, BcwSource>
  eezByUnit: Record<string, string[]>
  restoration: Restoration
  ranks: Record<'ncw' | 'gcw' | 'bcw', Record<string, { rank: number; of: number }>>
}

const url = (file: string) => `${import.meta.env.BASE_URL}data/${file}`

async function getJson<T>(file: string): Promise<T> {
  const res = await fetch(url(file))
  if (!res.ok) throw new Error(`Cannot load ${file} (${res.status})`)
  return res.json() as Promise<T>
}

export async function loadDataset(): Promise<Dataset> {
  const [list, global, aggregates, land, eez, sourceList, restoration] = await Promise.all([
    getJson<Unit[]>('units.json'),
    getJson<GlobalTotals>('global.json'),
    getJson<Aggregates>('aggregates.json'),
    getJson<FeatureCollection>('land.geojson'),
    getJson<FeatureCollection>('eez.geojson'),
    getJson<BcwSource[]>('bcw_sources.json'),
    getJson<Restoration>('restoration.json'),
  ])
  const units = Object.fromEntries(list.map((u) => [u.UNIT_CODE, u]))
  // Restoration results are attached to each unit as `<field>@<soil scenario>`, so map layers
  // and panel rows read them like any other unit field.
  for (const [code, byScenario] of Object.entries(restoration.units)) {
    const u = units[code]
    if (!u) continue
    for (const [soil, values] of Object.entries(byScenario)) for (const [k, v] of Object.entries(values ?? {})) u[`${k}@${soil}`] = v
  }
  const sources = Object.fromEntries(sourceList.map((s) => [s.code, s]))
  const eezByUnit: Record<string, string[]> = {}
  const eezCoords: Record<string, unknown[]> = {}
  for (const f of eez.features) {
    const unit = f.properties.unit ?? f.properties.code
    ;(eezByUnit[unit] ??= []).push(f.properties.code)
    ;(eezCoords[unit] ??= []).push(f.geometry.coordinates)
  }
  const bounds: Record<string, Bounds> = {}
  // Land extent wins; the extent of all its EEZ parts serves a unit with only a marine account.
  for (const [unit, coords] of Object.entries(eezCoords)) bounds[unit] = featureBounds(coords)
  for (const f of land.features) bounds[f.properties.code] = featureBounds(f.geometry.coordinates)
  return {
    units, list, global, aggregates, land, eez, bounds, sources, eezByUnit, restoration,
    ranks: {
      ncw: rank(list, 'ncw_usd2015_yr_mean'),
      gcw: rank(list, 'gcw_usd2015_yr_mean'),
      bcw: rank(list, 'bcw_usd2015_yr_mean'),
    },
  }
}

// Display name of a BCW source record: its territory, or the record name when the territory
// is shared by several records (Belize and Sapodilla Cayes are both in the territory "Belize").
export function sourceLabel(data: Dataset, code: string) {
  const s = data.sources[code]
  if (!s) return code
  const shared = Object.values(data.sources).filter((o) => o.territory && o.territory === s.territory).length > 1
  return (shared ? s.name : s.territory ?? s.name) ?? code
}

const curveCache = new Map<string, Promise<Curves>>()

// Restoration curves are loaded only when a country card asks for them.
export function loadCurves(code: string) {
  if (!curveCache.has(code)) curveCache.set(code, getJson<Curves>(`curves/${code}.json`))
  return curveCache.get(code)!
}

// Descending rank among units with an available value (descriptive only).
function rank(list: Unit[], field: string) {
  const valid = list.filter((u) => typeof u[field] === 'number').sort((a, b) => (b[field] as number) - (a[field] as number))
  return Object.fromEntries(valid.map((u, i) => [u.UNIT_CODE, { rank: i + 1, of: valid.length }]))
}

// Extent in both longitude conventions; the narrower one handles units crossing 180°.
function featureBounds(coordinates: unknown): Bounds {
  let minY = 90, maxY = -90
  let minA = 180, maxA = -180, minB = 360, maxB = 0
  const visit = (c: unknown) => {
    if (Array.isArray(c) && typeof c[0] === 'number') {
      const [x, y] = c as [number, number]
      const x360 = x < 0 ? x + 360 : x
      minA = Math.min(minA, x); maxA = Math.max(maxA, x)
      minB = Math.min(minB, x360); maxB = Math.max(maxB, x360)
      minY = Math.min(minY, y); maxY = Math.max(maxY, y)
    } else if (Array.isArray(c)) c.forEach(visit)
  }
  visit(coordinates)
  const useB = maxB - minB < maxA - minA
  const [lo, hi] = useB ? [minB, maxB] : [minA, maxA]
  let cx = (lo + hi) / 2
  if (cx > 180) cx -= 360
  return { center: [cx, (minY + maxY) / 2], width: hi - lo, height: maxY - minY }
}

export function zoomFor(b: Bounds) {
  const span = Math.max(b.width / 360, b.height / 170, 1e-3)
  return Math.min(8.5, Math.max(1.4, Math.log2(1 / span) - 0.4))
}
