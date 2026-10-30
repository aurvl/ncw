import * as maplibregl from 'maplibre-gl'
import type { ExpressionSpecification, MapLayerMouseEvent, Map as MLMap, StyleSpecification } from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import { useEffect, useRef, useState } from 'react'
import { zoomFor, type Dataset } from '../lib/data'
import { paintFor, resolveLayer, type LayerKey } from '../lib/layers'
import type { Soil, Theme } from '../lib/types'

type Props = {
  data: Dataset
  layer: LayerKey
  soil: Soil
  theme: Theme
  interactive: boolean
  selected: string | null
  panelOpen: boolean
  focus: string[] | null
  onSelect: (code: string) => void
  // `code` is the accounting unit; `source` is the BCW source record under the pointer on marine layers.
  onHover: (hover: { code: string; source?: string; x: number; y: number } | null) => void
  labels: { group: string; recentre: string; zoomIn: string; zoomOut: string }
}

// Point MapLibre at its bundled worker explicitly so dev and production builds both find it.
maplibregl.setWorkerUrl(workerUrl)

// Default view, used at start, by the recentre button and when a country card is closed.
const HOME = { center: [12, 18] as [number, number], zoom: 1.55 }

const css = (name: string) => getComputedStyle(document.documentElement).getPropertyValue(name).trim()

// Diagonal red hatching on the no-data grey: the paper's "reported zero" convention.
function hatchImage(base: string, line: string) {
  const size = 16
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = size
  const ctx = canvas.getContext('2d')!
  ctx.fillStyle = base
  ctx.fillRect(0, 0, size, size)
  ctx.strokeStyle = line
  ctx.lineWidth = 2
  for (const o of [-size, 0, size]) {
    ctx.beginPath()
    ctx.moveTo(o, 0)
    ctx.lineTo(o + size, size)
    ctx.stroke()
  }
  return ctx.getImageData(0, 0, size, size)
}

// Colours, zero flags, hover and selection are feature states: changing them only
// updates paint buffers, without re-tiling the GeoJSON sources.
const state = (key: string) => ['boolean', ['feature-state', key], false] as ExpressionSpecification
const fillFromState = (fallback: string) => ['coalesce', ['feature-state', 'fill'], fallback] as ExpressionSpecification
const showWhen = (key: string) => ['case', state(key), 1, 0] as ExpressionSpecification
const dimmed = ['case', state('dim'), 0.22, 1] as ExpressionSpecification

export default function Globe({ data, layer, soil, theme, interactive, selected, panelOpen, focus, onSelect, onHover, labels }: Props) {
  const container = useRef<HTMLDivElement>(null)
  const mapRef = useRef<MLMap | null>(null)
  const [ready, setReady] = useState(false)
  const callbacks = useRef({ onSelect, onHover })
  callbacks.current = { onSelect, onHover }

  // Create the map once.
  useEffect(() => {
    const style: StyleSpecification = {
      version: 8,
      projection: { type: 'globe' },
      sources: {
        land: { type: 'geojson', data: data.land as never, promoteId: 'code' },
        eez: { type: 'geojson', data: data.eez as never, promoteId: 'code' },
      },
      layers: [
        { id: 'ocean', type: 'background', paint: { 'background-color': css('--ocean') } },
        { id: 'eez-fill', type: 'fill', source: 'eez', paint: { 'fill-color': fillFromState(css('--missing')), 'fill-opacity': dimmed } },
        { id: 'eez-zero', type: 'fill', source: 'eez', paint: { 'fill-pattern': 'hatch', 'fill-opacity': showWhen('zero') } },
        { id: 'eez-line', type: 'line', source: 'eez', paint: { 'line-color': css('--border-map'), 'line-width': 0.3, 'line-opacity': 0.6 } },
        { id: 'land-fill', type: 'fill', source: 'land', paint: { 'fill-color': fillFromState(css('--missing')), 'fill-opacity': dimmed } },
        { id: 'land-zero', type: 'fill', source: 'land', paint: { 'fill-pattern': 'hatch', 'fill-opacity': showWhen('zero') } },
        { id: 'land-zero-line', type: 'line', source: 'land', paint: { 'line-color': css('--zero-edge'), 'line-width': 1.2, 'line-opacity': showWhen('zero') } },
        { id: 'land-line', type: 'line', source: 'land', paint: { 'line-color': css('--border-map'), 'line-width': 0.35, 'line-opacity': 0.7 } },
        { id: 'hover-line', type: 'line', source: 'land', paint: { 'line-color': css('--text'), 'line-width': 1.2, 'line-opacity': showWhen('hover') } },
        { id: 'selected-eez', type: 'line', source: 'eez', paint: { 'line-color': css('--accent'), 'line-width': 1.6, 'line-dasharray': [2, 1.5], 'line-opacity': showWhen('selected') } },
        { id: 'selected-line', type: 'line', source: 'land', paint: { 'line-color': css('--accent'), 'line-width': 2.4, 'line-opacity': showWhen('selected') } },
      ],
    }
    const map = new maplibregl.Map({
      container: container.current!,
      style,
      center: HOME.center,
      zoom: HOME.zoom,
      attributionControl: false,
      renderWorldCopies: false,
      maxZoom: 11,
    })
    // The hatch pattern is generated on demand, the first time a layer asks for it.
    map.setMissingStyleImageResolver((id) => {
      if (id === 'hatch' && !map.hasImage('hatch')) map.addImage('hatch', hatchImage(css('--missing'), css('--zero-edge')), { pixelRatio: 2 })
    })
    map.on('load', () => setReady(true))
    let hovered: string | null = null
    const setHovered = (code: string | null) => {
      if (hovered === code) return
      if (hovered) map.setFeatureState({ source: 'land', id: hovered }, { hover: false })
      if (code) map.setFeatureState({ source: 'land', id: code }, { hover: true })
      hovered = code
    }
    // EEZ polygons are BCW source records; a click or hover resolves to their accounting unit.
    const unitOf = (e: MapLayerMouseEvent) => {
      const p = e.features?.[0]?.properties
      return p ? { code: (p.unit ?? p.code) as string, source: p.unit ? (p.code as string) : undefined } : null
    }
    for (const id of ['land-fill', 'eez-fill']) {
      map.on('click', id, (e: MapLayerMouseEvent) => {
        const hit = unitOf(e)
        if (hit) callbacks.current.onSelect(hit.code)
      })
      map.on('mousemove', id, (e: MapLayerMouseEvent) => {
        const hit = unitOf(e)
        map.getCanvas().style.cursor = hit ? 'pointer' : ''
        setHovered(hit?.code ?? null)
        if (hit) callbacks.current.onHover({ ...hit, x: e.point.x, y: e.point.y })
      })
      map.on('mouseleave', id, () => {
        map.getCanvas().style.cursor = ''
        setHovered(null)
        callbacks.current.onHover(null)
      })
    }
    mapRef.current = map
    return () => {
      map.remove()
      mapRef.current = null
      setReady(false)
    }
  }, [data])

  // Layer colours and theme.
  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    const def = resolveLayer(layer, soil)
    const marine = def.target === 'eez'
    const missing = css('--missing')
    map.setPaintProperty('ocean', 'background-color', css('--ocean'))
    for (const [id, prop, token] of [['land-line', 'line-color', '--border-map'], ['eez-line', 'line-color', '--border-map'],
      ['hover-line', 'line-color', '--text'], ['selected-line', 'line-color', '--accent'], ['selected-eez', 'line-color', '--accent']] as const) {
      map.setPaintProperty(id, prop, css(token))
    }
    // Keep the feature-state expression in every mode (switching to a constant breaks MapLibre's
    // paint buffers); marine layers clear land states so the neutral fallback shows.
    map.setPaintProperty('land-fill', 'fill-color', fillFromState(marine ? css('--land-neutral') : missing))
    map.setPaintProperty('eez-fill', 'fill-color', fillFromState(missing))
    map.setLayoutProperty('eez-fill', 'visibility', marine ? 'visible' : 'none')
    map.setLayoutProperty('eez-line', 'visibility', marine ? 'visible' : 'none')
    map.setLayoutProperty('eez-zero', 'visibility', marine ? 'visible' : 'none')
    for (const u of data.list) {
      const paint = paintFor(u, def)
      const fill = paint.kind === 'class' ? paint.color : null
      map.setFeatureState({ source: 'land', id: u.UNIT_CODE }, { fill: marine ? null : fill, zero: !marine && paint.kind === 'zero' })
      // Every source record counted in the unit takes the unit's value.
      for (const id of data.eezByUnit[u.UNIT_CODE] ?? []) {
        if (marine) map.setFeatureState({ source: 'eez', id }, { fill })
        map.setFeatureState({ source: 'eez', id }, { zero: marine && paint.kind === 'zero' })
      }
    }
    if (map.hasImage('hatch')) map.updateImage('hatch', hatchImage(missing, css('--zero-edge')))
  }, [data, layer, soil, theme, ready])

  // Aggregate focus: units outside the selected region or group are dimmed.
  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    const members = focus ? new Set(focus) : null
    for (const u of data.list) {
      const dim = !!members && !members.has(u.UNIT_CODE)
      map.setFeatureState({ source: 'land', id: u.UNIT_CODE }, { dim })
      for (const id of data.eezByUnit[u.UNIT_CODE] ?? []) map.setFeatureState({ source: 'eez', id }, { dim })
    }
  }, [focus, ready, data])

  // Interaction handlers follow the page: the landing globe only rotates.
  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    const handlers = [map.dragPan, map.scrollZoom, map.dragRotate, map.doubleClickZoom, map.touchZoomRotate, map.keyboard, map.boxZoom]
    handlers.forEach((h) => (interactive ? h.enable() : h.disable()))
    if (interactive) return
    let frame = 0
    const spin = () => {
      const c = map.getCenter()
      map.setCenter([c.lng + 0.04, c.lat])
      frame = requestAnimationFrame(spin)
    }
    frame = requestAnimationFrame(spin)
    return () => cancelAnimationFrame(frame)
  }, [interactive, ready])

  // Selection: highlight and fly to the unit; closing the card flies back home.
  const hadSelection = useRef(false)
  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    if (!selected) {
      if (hadSelection.current && interactive) map.flyTo({ ...HOME, duration: 1800, essential: true, padding: { top: 0, bottom: 0, left: 0, right: 0 } })
      hadSelection.current = false
      return
    }
    hadSelection.current = true
    const setSelected = (value: boolean) => {
      map.setFeatureState({ source: 'land', id: selected }, { selected: value })
      for (const id of data.eezByUnit[selected] ?? []) map.setFeatureState({ source: 'eez', id }, { selected: value })
    }
    setSelected(true)
    const b = data.bounds[selected]
    if (b) {
      const wide = window.innerWidth > 860
      map.flyTo({
        center: b.center,
        zoom: zoomFor(b),
        duration: 2200,
        curve: 1.5,
        essential: true,
        padding: panelOpen ? (wide ? { right: 440, left: 0, top: 0, bottom: 0 } : { bottom: window.innerHeight * 0.5, top: 0, left: 0, right: 0 }) : undefined,
      })
    }
    return () => {
      if (!mapRef.current) return
      setSelected(false)
    }
  }, [selected, ready, data, panelOpen, interactive])

  const zoomBy = (delta: number) => mapRef.current?.easeTo({ zoom: mapRef.current.getZoom() + delta, duration: 400 })
  const recentre = () => mapRef.current?.flyTo({ ...HOME, duration: 1600, essential: true })

  return (
    <>
      <div ref={container} className="globe" />
      {interactive && (
        <div className="map-controls card" role="group" aria-label={labels.group}>
          <button onClick={recentre} aria-label={labels.recentre} title={labels.recentre}>
            <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><circle cx="12" cy="12" r="7" fill="none" stroke="currentColor" strokeWidth="1.6" /><circle cx="12" cy="12" r="2" fill="currentColor" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" /></svg>
          </button>
          <button onClick={() => zoomBy(1)} aria-label={labels.zoomIn} title={labels.zoomIn}>
            <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg>
          </button>
          <button onClick={() => zoomBy(-1)} aria-label={labels.zoomOut} title={labels.zoomOut}>
            <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M5 12h14" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg>
          </button>
        </div>
      )}
    </>
  )
}
