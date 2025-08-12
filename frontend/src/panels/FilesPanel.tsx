import React from 'react'

export default function FilesPanel() {
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
    <div className="row">
      <div className="col panel">
        <h3 className="section-title">Configs (data/configs)</h3>
        <div className="toolbar">
          <select onChange={e => readConfig(e.target.value)} value={selectedConfig}>
            <option value="">Select config</option>
            {configs.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <button className="btn secondary" onClick={loadLists}>Refresh</button>
        </div>
        <textarea rows={16} style={{ width: '100%', marginTop: 8 }} value={configText} onChange={e => setConfigText(e.target.value)} />
        <div className="toolbar">
          <button className="btn" onClick={saveConfig} disabled={!selectedConfig}>Save Config</button>
          <label className="btn ghost">
            Upload
            <input type="file" accept=".json,.yml,.yaml" style={{ display: 'none' }} onChange={async e => {
              const f = e.target.files?.[0]; if (!f) return; const t = await f.text(); setConfigText(t)
            }} />
          </label>
        </div>
      </div>
      <div className="col panel">
        <h3 className="section-title">Deck Files (data/decks)</h3>
        <div className="toolbar">
          <select onChange={e => readDeck(e.target.value)} value={selectedDeck}>
            <option value="">Select deck</option>
            {decks.map(d => <option key={d} value={d}>{d}</option>)}
          </select>
          <button className="btn secondary" onClick={loadLists}>Refresh</button>
        </div>
        <textarea rows={16} style={{ width: '100%', marginTop: 8 }} value={deckText} onChange={e => setDeckText(e.target.value)} />
        <div className="toolbar">
          <button className="btn" onClick={saveDeck} disabled={!selectedDeck}>Save Deck</button>
          <label className="btn ghost">
            Upload
            <input type="file" accept=".json,.yml,.yaml" style={{ display: 'none' }} onChange={async e => {
              const f = e.target.files?.[0]; if (!f) return; const t = await f.text(); setDeckText(t)
            }} />
          </label>
        </div>
      </div>
    </div>
  )
}


