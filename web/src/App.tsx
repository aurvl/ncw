import { AnimatePresence } from 'motion/react'
import { useEffect, useLayoutEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import AggregatePanel from './components/AggregatePanel'
import CountryPanel from './components/CountryPanel'
import Globe from './components/Globe'
import Header from './components/Header'
import LayerSwitch from './components/LayerSwitch'
import Legend from './components/Legend'
import MethodsDrawer from './components/MethodsDrawer'
import Search from './components/Search'
import Tooltip from './components/Tooltip'
import { loadDataset, type Dataset } from './lib/data'
import { LAYERS, type LayerKey } from './lib/layers'
import type { Theme } from './lib/types'
import Landing from './pages/Landing'

function initialTheme(): Theme {
  return document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light'
}

export default function App() {
  const { t } = useTranslation()
  const [data, setData] = useState<Dataset | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState<'landing' | 'explorer'>('landing')
  const [theme, setTheme] = useState<Theme>(initialTheme)
  const [layer, setLayer] = useState<LayerKey>('ncw')
  const [selected, setSelected] = useState<string | null>(null)
  const [aggregate, setAggregate] = useState<{ kind: 'regions' | 'groups'; key: string } | null>(null)
  const [hover, setHover] = useState<{ code: string; x: number; y: number } | null>(null)
  const [methodsOpen, setMethodsOpen] = useState(false)

  useEffect(() => {
    loadDataset().then(setData).catch((e: Error) => setError(e.message))
  }, [])

  // Layout effect: the theme attribute must change before the globe's effects read the CSS colours.
  useLayoutEffect(() => {
    document.documentElement.dataset.theme = theme
  }, [theme])

  // Only a toggle click is remembered, so visitors who never toggle keep the time-based theme.
  const toggleTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
    try { localStorage.setItem('ncw-theme', next) } catch { /* ignore */ }
  }

  const explore = page === 'explorer'
  const def = LAYERS[layer]
  const aggregateKind = def.kind === 'categories' ? def.aggregate : undefined
  // On an aggregate layer a click opens the totals of the clicked unit's region or group.
  const select = (code: string, fromMap = true) => {
    setPage('explorer')
    const key = fromMap && aggregateKind && def.kind === 'categories' && data ? def.category(data.units[code]) : null
    if (key && aggregateKind) {
      setSelected(null)
      setAggregate({ kind: aggregateKind, key })
    } else {
      setAggregate(null)
      setSelected(code)
    }
  }
  const changeLayer = (next: LayerKey) => {
    setLayer(next)
    setAggregate(null)
  }
  const focus = useMemo(() => {
    if (!aggregate || !data || def.kind !== 'categories') return null
    return data.list.filter((u) => def.category(u) === aggregate.key).map((u) => u.UNIT_CODE)
  }, [aggregate, data, def])

  return (
    <div className={`app ${explore ? 'is-explorer' : 'is-landing'}`}>
      {data && (
        <Globe
          data={data}
          layer={layer}
          theme={theme}
          interactive={explore}
          selected={selected}
          panelOpen={!!selected || !!aggregate}
          focus={focus}
          onSelect={select}
          onHover={explore ? setHover : () => {}}
          labels={{ group: t('controls.group'), recentre: t('controls.recentre'), zoomIn: t('controls.zoomIn'), zoomOut: t('controls.zoomOut') }}
        />
      )}
      <Header
        theme={theme}
        onTheme={toggleTheme}
        onHome={() => { setPage('landing'); setSelected(null); setAggregate(null) }}
        onExplore={() => setPage('explorer')}
        onMethods={() => setMethodsOpen(true)}
        explore={explore}
      />
      {error && <div className="load-error">{error}</div>}
      {!data && !error && <div className="loading" aria-live="polite"><span className="spinner" /></div>}

      <AnimatePresence>
        {!explore && data && <Landing key="landing" global={data.global} onExplore={() => setPage('explorer')} />}
      </AnimatePresence>

      {explore && data && (
        <>
          <div className="explorer-top">
            <Search data={data} onSelect={(code) => select(code, false)} />
          </div>
          <LayerSwitch layer={layer} onChange={changeLayer} />
          <Legend layer={layer} data={data} />
          {!selected && !aggregate && <p className="hint">{t(aggregateKind ? 'explorer.hintAggregate' : 'explorer.hint')}</p>}
          {hover && hover.code !== selected && <Tooltip data={data} layer={layer} hover={hover} />}
          <AnimatePresence>
            {selected && data.units[selected] && (
              <CountryPanel key={selected} data={data} code={selected} onClose={() => setSelected(null)} />
            )}
            {aggregate && (
              <AggregatePanel key={`${aggregate.kind}-${aggregate.key}`} data={data} kind={aggregate.kind} name={aggregate.key}
                              onClose={() => setAggregate(null)} />
            )}
          </AnimatePresence>
        </>
      )}

      <AnimatePresence>
        {methodsOpen && <MethodsDrawer onClose={() => setMethodsOpen(false)} />}
      </AnimatePresence>
    </div>
  )
}
