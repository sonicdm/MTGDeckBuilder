import React, { useState } from 'react'
import YAML from 'js-yaml'
import BuilderForm from './panels/BuilderForm'
import FilesPanel from './panels/FilesPanel'
import DeckAnalysis from './panels/DeckAnalysis'
import DeckViewer from './panels/DeckViewer'

type DeckItem = {
  qty: number
  name: string
  type: string
  mv: number
  types?: string[]
  is_creature?: boolean
  reasons?: string[]
  text?: string
  mana_cost?: string
  rarity?: string
  colors?: string[]
  power?: number | null
  toughness?: number | null
  loyalty?: number | null
  set_code?: string | null
  color_identity?: string[]
}

type BuildContextSummary = {
  operations?: string[]
  unmet_conditions?: string[]
  category_summary?: Record<string, { target: number; added: number; remaining: number }>
}

type BuildResponse = {
  decklist: DeckItem[]
  analysis: any
  arena_import: string
  build_log?: string[]
  build_context?: BuildContextSummary
}

export default function App() {
  const [yamlText, setYamlText] = useState('')
  const [result, setResult] = useState<BuildResponse | null>(null)
  const [savePath, setSavePath] = useState('')
  const [yamlCollapsed, setYamlCollapsed] = useState(false)
  const [viewerDeck, setViewerDeck] = useState<any>(null)
  const [buildLog, setBuildLog] = useState<string[]>([])
  const [buildContext, setBuildContext] = useState<BuildContextSummary | null>(null)

  React.useEffect(() => {
    console.debug('[App] yamlText updated, length:', yamlText.length)
  }, [yamlText])

  const [form, setForm] = useState<any>({
    deck: { name: '', colors: [], size: 60, max_card_copies: 4, legalities: [] },
    categories: {},
    mana_base: { land_count: 24 },
    card_constraints: {},
    priority_cards: [],
    scoring_rules: {},
    fallback_strategy: {}
  })

  // Auto-generate YAML from form
  React.useEffect(() => {
    try { setYamlText(YAML.dump(form)) } catch {}
  }, [form])

  async function build() {
    const res = await fetch('/api/build', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ yaml_text: yamlText, debug: true })
    })
    if (!res.ok) {
      alert('Build failed')
      return
    }
    const data = await res.json()
    setResult(data)
    setBuildLog(Array.isArray(data.build_log) ? data.build_log : [])
    setBuildContext(data.build_context || null)
  }

  function updateForm(path: string, value: any) {
    setForm((prev: any) => {
      const copy = JSON.parse(JSON.stringify(prev))
      const parts = path.split('.')
      let cur = copy
      for (let i = 0; i < parts.length - 1; i++) {
        if (!(parts[i] in cur)) cur[parts[i]] = {}
        cur = cur[parts[i]]
      }
      cur[parts[parts.length - 1]] = value
      return copy
    })
  }

  function formToYaml() {
    try {
      const text = YAML.dump(form)
      setYamlText(text)
    } catch (e) {
      alert('Failed to serialize YAML')
    }
  }

  async function onUploadFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const text = await file.text()
    setYamlText(text)
  }

  async function saveYaml() {
    if (!savePath) {
      alert('Enter a relative save path under data/configs, e.g. my-deck.yaml')
      return
    }
    let cfg: any
    try {
      cfg = YAML.load(yamlText)
      if (!cfg || typeof cfg !== 'object') throw new Error('Invalid YAML')
    } catch (e) {
      alert('YAML is invalid: ' + (e as Error).message)
      return
    }
    const res = await fetch('/api/config/save_yaml', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: savePath, config: cfg })
    })
    if (!res.ok) {
      const t = await res.text()
      alert('Save failed: ' + t)
      return
    }
    alert('Saved to ' + savePath)
  }

  const [activeTab, setActiveTab] = useState<'builder'|'inventory'|'viewer'|'files'>('builder')

  function TabButton({ id, label }: { id: typeof activeTab; label: string }) {
    return (
      <button
        onClick={() => setActiveTab(id)}
        style={{ padding: 8, marginRight: 8, fontWeight: activeTab === id ? 'bold' : 'normal' }}
      >{label}</button>
    )
  }

  return (
    <div style={{ padding: 16, fontFamily: 'sans-serif' }}>
      <div style={{ marginBottom: 12 }}>
        <TabButton id='builder' label='Deck Builder' />
        <TabButton id='inventory' label='Inventory Manager' />
        <TabButton id='viewer' label='Deck Viewer' />
        <TabButton id='files' label='Deck/Config Listings' />
      </div>

      {activeTab === 'builder' && (
        <>
      <h2>Builder</h2>
      <BuilderForm form={form} setForm={setForm} onYamlLoaded={setYamlText} onBuild={build} />
      <div className="row" style={{ marginTop: 16 }}>
        <div className="col panel">
          <h3 className="section-title">Decklist</h3>
          {result ? (
            <>
              <DeckList decklist={result.decklist} />
              <div className="toolbar" style={{ marginTop: 8 }}>
                <button className="btn" onClick={() => { setViewerDeck(result); setActiveTab('viewer') }}>Open in Deck Viewer</button>
              </div>
            </>
          ) : <div className="hint">Build to preview deck contents.</div>}
        </div>
        <div className="col panel">
          <div className="toolbar" style={{ justifyContent: 'space-between' }}>
            <h3 className="section-title" style={{ margin: 0 }}>YAML</h3>
            <button className="btn secondary" onClick={() => setYamlCollapsed(!yamlCollapsed)}>{yamlCollapsed ? 'Expand' : 'Collapse'}</button>
          </div>
          {!yamlCollapsed && (
            <>
              <textarea value={yamlText} onChange={e => setYamlText(e.target.value)} rows={14} style={{ width: '100%' }} />
              <div className="toolbar" style={{ marginTop: 8 }}>
                <button className="btn" onClick={build}>Build</button>
                <input placeholder="save path e.g. my-deck.yaml" value={savePath} onChange={e => setSavePath(e.target.value)} style={{ flex: 1 }} />
                <button className="btn secondary" onClick={saveYaml}>Save YAML</button>
                <label className="btn ghost">
                  Upload YAML
                  <input type="file" accept=".yml,.yaml" style={{ display: 'none' }} onChange={onUploadFile} />
                </label>
              </div>
              {buildLog.length > 0 && (
                <div style={{ marginTop: 8, border: '1px solid #1f2937', borderRadius: 8, padding: 8, maxHeight: 200, overflow: 'auto' }}>
                  <div className="section-title">Build Log</div>
                  <pre style={{ whiteSpace: 'pre-wrap' }}>{buildLog.join('\n')}</pre>
                </div>
              )}
              {buildContext && (
                <div style={{ marginTop: 8, border: '1px solid #1f2937', borderRadius: 8, padding: 8, maxHeight: 260, overflow: 'auto' }}>
                  <div className="section-title">Debug Context</div>
                  {buildContext.unmet_conditions && buildContext.unmet_conditions.length > 0 && (
                    <div style={{ marginBottom: 8 }}>
                      <div className="hint" style={{ marginBottom: 4 }}>Unmet Conditions</div>
                      <ul>
                        {buildContext.unmet_conditions.map((u, i) => <li key={i}>{u}</li>)}
                      </ul>
                    </div>
                  )}
                  {buildContext.category_summary && (
                    <div style={{ marginBottom: 8 }}>
                      <div className="hint" style={{ marginBottom: 4 }}>Category Summary</div>
                      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                          <tr>
                            <th style={{ textAlign: 'left', padding: '6px 8px' }}>Category</th>
                            <th style={{ textAlign: 'right', padding: '6px 8px' }}>Target</th>
                            <th style={{ textAlign: 'right', padding: '6px 8px' }}>Added</th>
                            <th style={{ textAlign: 'right', padding: '6px 8px' }}>Remaining</th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(buildContext.category_summary).map(([k, v]) => (
                            <tr key={k} style={{ borderTop: '1px solid #1f2937' }}>
                              <td style={{ padding: '6px 8px' }}>{k}</td>
                              <td style={{ padding: '6px 8px', textAlign: 'right' }}>{v.target}</td>
                              <td style={{ padding: '6px 8px', textAlign: 'right' }}>{v.added}</td>
                              <td style={{ padding: '6px 8px', textAlign: 'right' }}>{v.remaining}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  {buildContext.operations && buildContext.operations.length > 0 && (
                    <details>
                      <summary>Operations ({buildContext.operations.length})</summary>
                      <pre style={{ whiteSpace: 'pre-wrap' }}>{buildContext.operations.join('\n')}</pre>
                    </details>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
      {result && <DeckAnalysis decklist={result.decklist} />}
        </>
      )}

      {activeTab === 'inventory' && (
        <div>
          <h3>Inventory Manager</h3>
          <p>Coming soon: list inventory files, upload/edit .txt, save to /data/inventory.</p>
        </div>
      )}

      {activeTab === 'viewer' && (
        <DeckViewer decklist={viewerDeck?.decklist || []} arena={viewerDeck?.arena_import} analysis={viewerDeck?.analysis} />
      )}

      {activeTab === 'files' && <FilesPanel />}
    </div>
  )
}

function DeckList({ decklist }: { decklist: DeckItem[] }) {
  const rows = decklist || []
  return (
    <div style={{ maxHeight: 300, overflow: 'auto', border: '1px solid #1f2937', borderRadius: 8 }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead style={{ position: 'sticky', top: 0, background: '#0b1220' }}>
          <tr>
            <th style={{ textAlign: 'left', padding: '8px 10px' }}>Qty</th>
            <th style={{ textAlign: 'left', padding: '8px 10px' }}>Name</th>
            <th style={{ textAlign: 'left', padding: '8px 10px' }}>Type</th>
            <th style={{ textAlign: 'right', padding: '8px 10px' }}>MV</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, idx) => {
            const reasonTip = (r.reasons && r.reasons.length > 0) ? r.reasons.join('\n') : ''
            return (
              <tr key={idx} style={{ borderTop: '1px solid #1f2937' }} title={reasonTip}>
                <td style={{ padding: '6px 10px' }}>{r.qty}</td>
                <td style={{ padding: '6px 10px' }}>{r.name}</td>
                <td style={{ padding: '6px 10px' }}>
                  {r.type}
                  {r.is_creature ? <span className="chip" style={{ marginLeft: 6 }}>Creature</span> : null}
                </td>
                <td style={{ padding: '6px 10px', textAlign: 'right' }}>{r.mv}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}


function DeckFilesPanel() {
  const [configs, setConfigs] = React.useState<string[]>([])
  const [selectedConfig, setSelectedConfig] = React.useState<string>('')
  const [configText, setConfigText] = React.useState<string>('')
  const [decks, setDecks] = React.useState<string[]>([])
  const [selectedDeck, setSelectedDeck] = React.useState<string>('')
  const [deckText, setDeckText] = React.useState<string>('')

  async function loadLists() {
    const c = await fetch('/api/config/files').then(r => r.json())
    setConfigs([...(c.json || []), ...(c.yaml || [])])
    const d = await fetch('/api/decks').then(r => r.json())
    setDecks([...(d.yaml || []), ...(d.json || [])])
  }
  React.useEffect(() => { loadLists() }, [])

  async function readConfig(path: string) {
    if (!path) return
    const r = await fetch('/api/config/file?path=' + encodeURIComponent(path)).then(r => r.json())
    setSelectedConfig(path)
    setConfigText(r.text)
  }
  async function saveConfig() {
    if (!selectedConfig) return
    await fetch('/api/config/file', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ path: selectedConfig, text: configText }) })
    alert('Saved config')
  }

  async function readDeck(path: string) {
    if (!path) return
    const r = await fetch('/api/decks/file?path=' + encodeURIComponent(path)).then(r => r.json())
    setSelectedDeck(path)
    setDeckText(r.text)
  }
  async function saveDeck() {
    if (!selectedDeck) return
    await fetch('/api/decks/file', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ path: selectedDeck, text: deckText }) })
    alert('Saved deck')
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
      <div>
        <h3>Configs</h3>
        <div style={{ display: 'flex', gap: 8 }}>
          <select onChange={e => readConfig(e.target.value)} value={selectedConfig}>
            <option value="">Select config</option>
            {configs.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <button onClick={loadLists}>Refresh</button>
        </div>
        <textarea rows={12} style={{ width: '100%', marginTop: 8 }} value={configText} onChange={e => setConfigText(e.target.value)} />
        <div>
          <button onClick={saveConfig} disabled={!selectedConfig}>Save Config</button>
          <label style={{ marginLeft: 8 }}>
            Upload
            <input type="file" accept=".json" style={{ display: 'none' }} onChange={async e => {
              const f = e.target.files?.[0]; if (!f) return; const t = await f.text(); setConfigText(t)
            }} />
          </label>
        </div>
      </div>
      <div>
        <h3>Deck YAMLs</h3>
        <div style={{ display: 'flex', gap: 8 }}>
          <select onChange={e => readDeck(e.target.value)} value={selectedDeck}>
            <option value="">Select deck</option>
            {decks.map(d => <option key={d} value={d}>{d}</option>)}
          </select>
          <button onClick={loadLists}>Refresh</button>
        </div>
        <textarea rows={12} style={{ width: '100%', marginTop: 8 }} value={deckText} onChange={e => setDeckText(e.target.value)} />
        <div>
          <button onClick={saveDeck} disabled={!selectedDeck}>Save Deck</button>
          <label style={{ marginLeft: 8 }}>
            Upload
            <input type="file" accept=".yml,.yaml" style={{ display: 'none' }} onChange={async e => {
              const f = e.target.files?.[0]; if (!f) return; const t = await f.text(); setDeckText(t)
            }} />
          </label>
        </div>
      </div>
    </div>
  )
}


