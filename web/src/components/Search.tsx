import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { Dataset } from '../lib/data'

const fold = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()

export default function Search({ data, onSelect }: { data: Dataset; onSelect: (code: string) => void }) {
  const { t } = useTranslation()
  const [query, setQuery] = useState('')
  const [active, setActive] = useState(0)
  const selectable = useMemo(
    () => data.list.filter((u) => u.name && data.bounds[u.UNIT_CODE]).sort((a, b) => a.name!.localeCompare(b.name!)),
    [data],
  )
  const results = useMemo(() => {
    const q = fold(query.trim())
    if (!q) return []
    return selectable.filter((u) => fold(u.name!).includes(q) || u.UNIT_CODE.toLowerCase() === q).slice(0, 8)
  }, [query, selectable])

  const choose = (code: string) => {
    onSelect(code)
    setQuery('')
  }

  return (
    <div className="search" role="combobox" aria-expanded={results.length > 0}>
      <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><circle cx="11" cy="11" r="6.5" fill="none" stroke="currentColor" strokeWidth="1.7" /><path d="M16 16l4.5 4.5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" /></svg>
      <input
        value={query}
        placeholder={t('explorer.search')}
        aria-label={t('explorer.search')}
        onChange={(e) => { setQuery(e.target.value); setActive(0) }}
        onKeyDown={(e) => {
          if (e.key === 'ArrowDown') setActive((a) => Math.min(a + 1, results.length - 1))
          if (e.key === 'ArrowUp') setActive((a) => Math.max(a - 1, 0))
          if (e.key === 'Enter' && results[active]) choose(results[active].UNIT_CODE)
          if (e.key === 'Escape') setQuery('')
        }}
      />
      {query.trim() && (
        <ul className="search-results card" role="listbox">
          {results.length === 0 && <li className="muted">{t('explorer.noMatch')}</li>}
          {results.map((u, i) => (
            <li key={u.UNIT_CODE} role="option" aria-selected={i === active} className={i === active ? 'active' : ''}
                onMouseDown={() => choose(u.UNIT_CODE)} onMouseEnter={() => setActive(i)}>
              {u.name}<span className="code">{u.UNIT_CODE}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
