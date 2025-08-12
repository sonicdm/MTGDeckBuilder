import React from 'react'
import DeckAnalysis from './DeckAnalysis'

type Row = {
  qty: number
  name: string
  type: string
  mv: number
  text?: string
  mana_cost?: string
  rarity?: string
  colors?: string[]
  reasons?: string[]
  score?: number | null
  power?: number | string | null
  toughness?: number | string | null
  loyalty?: number | string | null
  set_code?: string | null
}

type ColumnKey = 'qty' | 'name' | 'type' | 'mv' | 'mana_cost' | 'rarity' | 'colors' | 'set_code' | 'reasons' | 'score'

function DeckList({
  decklist,
  onHover,
  columns,
  sortKey,
  sortDir,
  onSort,
}: {
  decklist: Row[]
  onHover?: (row: Row | null) => void
  columns: ColumnKey[]
  sortKey: ColumnKey
  sortDir: 'asc' | 'desc'
  onSort: (key: ColumnKey) => void
}) {
  const rows = React.useMemo(() => {
    const copy = [...(decklist || [])]
    const cmp = (a: any, b: any) => (a < b ? -1 : a > b ? 1 : 0)
    copy.sort((a, b) => {
      const av = (a as any)[sortKey]
      const bv = (b as any)[sortKey]
      const base = cmp(String(av ?? ''), String(bv ?? ''))
      return sortDir === 'asc' ? base : -base
    })
    return copy
  }, [decklist, sortKey, sortDir])

  const header = (key: ColumnKey, label: string, align: 'left' | 'right' = 'left') => (
    <th
      style={{ textAlign: align, padding: '8px 10px', cursor: 'pointer' }}
      onClick={() => onSort(key)}
    >
      {label} {sortKey === key ? (sortDir === 'asc' ? '▲' : '▼') : ''}
    </th>
  )

  return (
    <div style={{ maxHeight: 400, overflow: 'auto', border: '1px solid #1f2937', borderRadius: 8 }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead style={{ position: 'sticky', top: 0, background: '#0b1220' }}>
          <tr>
            {columns.includes('qty') && header('qty', 'Qty')}
            {columns.includes('name') && header('name', 'Name')}
            {columns.includes('type') && header('type', 'Type')}
            {columns.includes('mv') && header('mv', 'MV', 'right')}
            {columns.includes('mana_cost') && header('mana_cost', 'Cost')}
            {columns.includes('rarity') && header('rarity', 'Rarity')}
            {columns.includes('score') && header('score', 'Score', 'right')}
            {columns.includes('colors') && header('colors', 'Colors')}
            {columns.includes('set_code') && header('set_code', 'Set')}
            {columns.includes('reasons') && header('reasons', 'Reasons')}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, idx) => (
            <tr
              key={idx}
              style={{ borderTop: '1px solid #1f2937' }}
              onMouseEnter={() => onHover && onHover(r)}
              onMouseLeave={() => onHover && onHover(null)}
              title={(r.reasons || []).join('\n')}
            >
              {columns.includes('qty') && <td style={{ padding: '6px 10px' }}>{r.qty}</td>}
              {columns.includes('name') && <td style={{ padding: '6px 10px' }}>{r.name}</td>}
              {columns.includes('type') && <td style={{ padding: '6px 10px' }}>{r.type}</td>}
              {columns.includes('mv') && <td style={{ padding: '6px 10px', textAlign: 'right' }}>{r.mv}</td>}
              {columns.includes('mana_cost') && (
                <td style={{ padding: '6px 10px' }}>{r.mana_cost ? <ManaCost cost={r.mana_cost} /> : ''}</td>
              )}
              {columns.includes('rarity') && <td style={{ padding: '6px 10px' }}>{r.rarity || ''}</td>}
              {columns.includes('score') && <td style={{ padding: '6px 10px', textAlign: 'right' }}>{r.score ?? ''}</td>}
              {columns.includes('colors') && <td style={{ padding: '6px 10px' }}>{(r.colors || []).join(',')}</td>}
              {columns.includes('set_code') && <td style={{ padding: '6px 10px' }}>{r.set_code || ''}</td>}
              {columns.includes('reasons') && <td style={{ padding: '6px 10px', fontSize: 12, color: '#9ca3af' }}>{(r.reasons || []).join('; ')}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function DeckViewer({ decklist, arena, analysis }: { decklist: Row[]; arena?: string; analysis?: any }) {
  const [files, setFiles] = React.useState<string[]>([])
  const [selected, setSelected] = React.useState<string>('')
  const [status, setStatus] = React.useState<string>('')
  const [localDeck, setLocalDeck] = React.useState<Row[]>(decklist || [])
  const [localArena, setLocalArena] = React.useState<string | undefined>(arena)
  const [localAnalysis, setLocalAnalysis] = React.useState<any>(analysis)
  const [hovered, setHovered] = React.useState<Row | null>(null)
  const [columns, setColumns] = React.useState<ColumnKey[]>([
    'qty', 'name', 'type', 'mv', 'mana_cost', 'rarity', 'score', 'reasons'
  ])
  const [sortKey, setSortKey] = React.useState<ColumnKey>('name')
  const [sortDir, setSortDir] = React.useState<'asc' | 'desc'>('asc')

  React.useEffect(() => {
    setLocalDeck(decklist || [])
    setLocalArena(arena)
    setLocalAnalysis(analysis)
  }, [JSON.stringify(decklist), arena, JSON.stringify(analysis)])

  async function refreshList() {
    try {
      const d = await fetch('/api/decks').then(r => r.json())
      const list = [...(d.json || [])] // viewer expects saved deck JSONs
      setFiles(list)
    } catch (e) { setStatus('Failed to list deck files') }
  }
  React.useEffect(() => { refreshList() }, [])

  async function loadDeck(path: string) {
    if (!path) return
    try {
      const r = await fetch('/api/decks/file?path=' + encodeURIComponent(path)).then(r => r.json())
      const text = r.text || ''
      try {
        const parsed = JSON.parse(text)
        const rows: Row[] = parsed.decklist || []
        if (Array.isArray(rows)) setLocalDeck(rows)
        setLocalArena(parsed.arena)
        setLocalAnalysis(parsed.analysis)
        setStatus('Loaded ' + path)
      } catch {
        setStatus('Unsupported format in ' + path)
      }
    } catch (e) {
      setStatus('Failed to load ' + path)
    }
  }

  async function saveDeck() {
    const path = prompt('Save to data/decks path (e.g., my-deck.json):', selected || 'my-deck.json') || ''
    if (!path) return
    try {
      const body = { path, text: JSON.stringify({ decklist: localDeck, arena: localArena, analysis: localAnalysis }, null, 2) }
      const res = await fetch('/api/decks/file', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      if (!res.ok) throw new Error()
      setSelected(path)
      await refreshList()
      setStatus('Saved ' + path)
    } catch { setStatus('Save failed') }
  }
  async function copyArena() {
    try {
      await navigator.clipboard.writeText(arena || '')
      alert('Arena export copied to clipboard')
    } catch {}
  }

  async function saveSnapshot() {
    const path = prompt('Save snapshot to data/exports (e.g., my-deck.deck.json):', 'my-deck.deck.json') || ''
    if (!path) return
    try {
      const body = {
        path,
        deck_config: {},
        seed_yaml: '',
        build_hints: {},
        decklist: localDeck,
        analysis: localAnalysis || {},
        arena: localArena || ''
      }
      const res = await fetch('/api/snapshots/save', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      if (!res.ok) throw new Error()
      setStatus('Snapshot saved to ' + path)
    } catch { setStatus('Snapshot save failed') }
  }

  function toggleColumn(key: ColumnKey) {
    setColumns(prev => prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key])
  }

  function onSort(key: ColumnKey) {
    if (key === sortKey) setSortDir(d => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortKey(key); setSortDir('asc') }
  }

  return (
    <div className="panel">
      <h3 className="section-title">Deck Viewer</h3>
      <div className="toolbar" style={{ gap: 8, marginBottom: 8 }}>
        <select value={selected} onChange={e => { setSelected(e.target.value); loadDeck(e.target.value) }}>
          <option value="">Select deck file</option>
          {files.map(f => <option key={f} value={f}>{f}</option>)}
        </select>
        <button className="btn secondary" onClick={refreshList}>Refresh</button>
        <button className="btn" onClick={saveDeck}>Save Current</button>
        <button className="btn" onClick={saveSnapshot}>Save Snapshot</button>
        {status && <span className="hint">{status}</span>}
      </div>
      <div className="toolbar" style={{ gap: 12, marginBottom: 8, flexWrap: 'wrap' as any }}>
        <span className="hint">Columns:</span>
        {(['qty','name','type','mv','mana_cost','rarity','colors','set_code','reasons','score'] as ColumnKey[]).map(k => (
          <label key={k} style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <input type="checkbox" checked={columns.includes(k)} onChange={() => toggleColumn(k)} />
            <span style={{ fontSize: 12, color: '#e5e7eb' }}>{k}</span>
          </label>
        ))}
      </div>
      {localDeck && localDeck.length > 0 ? (
        <>
          <div className="row" style={{ gap: 16 }}>
            <div className="col" style={{ flex: 2 }}>
              <DeckList decklist={localDeck} onHover={setHovered} columns={columns} sortKey={sortKey} sortDir={sortDir} onSort={onSort} />
            </div>
            <div className="col" style={{ flex: 1 }}>
              {hovered ? (
                <div style={{ border: '1px solid #1f2937', borderRadius: 12, padding: 12, background: '#0b1220' }}>
                  <h4 className="section-title" style={{ marginTop: 0 }}>{hovered.name}</h4>
                  <div className="hint">{hovered.type}</div>
                  {hovered.mana_cost && <ManaCost cost={hovered.mana_cost} />}
                  <div style={{ marginTop: 8, fontSize: 13, whiteSpace: 'pre-wrap' }}>
                    <ManaText text={hovered.text || '—'} />
                  </div>
                  <div className="chips" style={{ marginTop: 8 }}>
                    <span className="chip">Qty {hovered.qty}</span>
                    <span className="chip">MV {hovered.mv}</span>
                    {hovered.rarity && <span className="chip">{hovered.rarity}</span>}
                    {String(hovered.type || '').toLowerCase().includes('creature') && (hovered.power || hovered.toughness) && (
                      <span className="chip">{String(hovered.power ?? '?')}/{String(hovered.toughness ?? '?')}</span>
                    )}
                    {String(hovered.type || '').toLowerCase().includes('planeswalker') && hovered.loyalty && (
                      <span className="chip">Loyalty {hovered.loyalty}</span>
                    )}
                  </div>
                  {Array.isArray(hovered.reasons) && hovered.reasons.length > 0 && (
                    <div style={{ marginTop: 10 }}>
                      <div className="hint" style={{ marginBottom: 4 }}>Reasons</div>
                      <ul style={{ margin: 0, paddingLeft: 18 }}>
                        {hovered.reasons.map((r, i) => <li key={i} style={{ fontSize: 12 }}>{r}</li>)}
                      </ul>
                    </div>
                  )}
                </div>
              ) : (
                <div className="hint">Hover a card to preview.</div>
              )}
              <div className="toolbar" style={{ marginTop: 8 }}>
                {localArena && <button className="btn" onClick={copyArena}>Copy Arena Export</button>}
              </div>
            </div>
          </div>
          <DeckAnalysis decklist={localDeck} analysis={localAnalysis} />
        </>
      ) : (
        <div className="hint">No deck loaded.</div>
      )}
    </div>
  )
}

function ManaCost({ cost }: { cost: string }) {
  // Convert a string like "{1}{R}{R}" to mana pip icons
  const tokens = String(cost).match(/\{[^}]+\}/g) || []
  const toClass = (tok: string) => {
    const v = tok.replace(/[{}]/g, '').toLowerCase()
    // maps like 'r', 'g', 'w', 'u', 'b', '2', 'x', etc.
    return `ms ms-${v} ms-cost`
  }
  return (
    <div className="chips" style={{ marginTop: 6 }}>
      {tokens.map((t, i) => <i key={i} className={toClass(t)} aria-hidden="true" />)}
    </div>
  )
}

function ManaText({ text }: { text: string }) {
  // Replace {...} symbols with mana pip icons inline
  // Normalize escaped newlines ("\n") to real newlines for display
  const normalized = text.replace(/\\n/g, '\n').replace(/\\r\\n/g, '\n')
  const parts = [] as React.ReactNode[]
  const regex = /\{[^}]+\}/g
  let lastIndex = 0
  let m: RegExpExecArray | null
  while ((m = regex.exec(normalized)) !== null) {
    const idx = m.index
    if (idx > lastIndex) parts.push(normalized.slice(lastIndex, idx))
    const token = m[0]
    const v = token.replace(/[{}]/g, '').toLowerCase()
    parts.push(<i key={idx} className={`ms ms-${v} ms-cost`} aria-hidden="true" />)
    lastIndex = idx + token.length
  }
  if (lastIndex < normalized.length) parts.push(normalized.slice(lastIndex))
  return <>{parts}</>
}


