import type { Aggregates, FeatureCollection, GlobalTotals, Unit } from './types'

export type Bounds = { center: [number, number]; width: number; height: number }

export type Dataset = {
  units: Record<string, Unit>
  list: Unit[]
  global: GlobalTotals
  aggregates: Aggregates
  land: FeatureCollection
  eez: FeatureCollection
  bounds: Record<string, Bounds>
  ranks: Record<'ncw' | 'gcw' | 'bcw', Record<string, { rank: number; of: number }>>
}

const url = (file: string) => `${import.meta.env.BASE_URL}data/${file}`

async function getJson<T>(file: string): Promise<T> {
  const res = await fetch(url(file))
  if (!res.ok) throw new Error(`Cannot load ${file} (${res.status})`)
  return res.json() as Promise<T>
}

export async function loadDataset(): Promise<Dataset> {
  const [list, global, aggregates, land, eez] = await Promise.all([
    getJson<Unit[]>('units.json'),
    getJson<GlobalTotals>('global.json'),
    getJson<Aggregates>('aggregates.json'),
    getJson<FeatureCollection>('land.geojson'),
    getJson<FeatureCollection>('eez.geojson'),
  ])
  const units = Object.fromEntries(list.map((u) => [u.UNIT_CODE, u]))
  const bounds: Record<string, Bounds> = {}
  // Land extent wins; EEZ extent serves units that only have a marine account.
  for (const fc of [eez, land]) for (const f of fc.features) bounds[f.properties.code] = featureBounds(f.geometry.coordinates)
  return {
    units, list, global, aggregates, land, eez, bounds,
    ranks: {
      ncw: rank(list, 'ncw_usd2015_yr_mean'),
      gcw: rank(list, 'gcw_usd2015_yr_mean'),
      bcw: rank(list, 'bcw_usd2015_yr_mean'),
    },
  }
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
