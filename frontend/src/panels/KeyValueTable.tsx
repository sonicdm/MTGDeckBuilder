import React from 'react'

type Pair = { key: string; value: string | number }
type Props = {
  label: string
  data: Record<string, any>
  onChange: (data: Record<string, any>) => void
}

export default function KeyValueTable({ label, data, onChange }: Props) {
  const entries = Object.entries(data || {}) as [string, any][]
  const [rows, setRows] = React.useState<Pair[]>(entries.map(([k, v]) => ({ key: k, value: v })))

  React.useEffect(() => {
    const e = Object.entries(data || {}) as [string, any][]
    setRows(e.map(([k, v]) => ({ key: k, value: v })))
  }, [JSON.stringify(data)])

  function updateRow(i: number, field: 'key' | 'value', val: string) {
    const next = rows.slice()
    ;(next[i] as any)[field] = val
    setRows(next)
    const obj: Record<string, any> = {}
    for (const r of next) {
      if ((r.key || '').trim()) obj[r.key] = isNaN(Number(r.value)) ? r.value : Number(r.value)
    }
    onChange(obj)
  }

  function addRow() {
    const next = rows.concat([{ key: '', value: '' }])
    setRows(next)
  }

  function removeRow(i: number) {
    const next = rows.slice(0, i).concat(rows.slice(i + 1))
    setRows(next)
    const obj: Record<string, any> = {}
    for (const r of next) {
      if ((r.key || '').trim()) obj[r.key] = isNaN(Number(r.value)) ? r.value : Number(r.value)
    }
    onChange(obj)
  }

  return (
    <div>
      <div className="toolbar" style={{ justifyContent: 'space-between' }}>
        <h4 className="section-title" style={{ margin: 0 }}>{label}</h4>
        <button className="btn secondary" onClick={addRow}>Add</button>
      </div>
      <div style={{ display: 'grid', gap: 8 }}>
        {rows.map((r, i) => (
          <div key={i} className="row" style={{ gap: 8 }}>
            <input placeholder="key" value={r.key} onChange={e => updateRow(i, 'key', e.target.value)} />
            <input placeholder="value" value={String(r.value ?? '')} onChange={e => updateRow(i, 'value', e.target.value)} />
            <button className="btn ghost" onClick={() => removeRow(i)}>Remove</button>
          </div>
        ))}
      </div>
    </div>
  )
}


