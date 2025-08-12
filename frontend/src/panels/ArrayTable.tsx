import React from 'react'

type Props = {
  label: string
  items: string[]
  onChange: (items: string[]) => void
  placeholder?: string
}

export default function ArrayTable({ label, items, onChange, placeholder }: Props) {
  const [rows, setRows] = React.useState<string[]>(items || [])
  React.useEffect(() => { setRows(items || []) }, [JSON.stringify(items)])

  function update(i: number, val: string) {
    const next = rows.slice(); next[i] = val; setRows(next); onChange(next.filter(s => (s || '').trim()))
  }
  function addRow() { setRows(rows.concat([''])) }
  function removeRow(i: number) { const next = rows.slice(0, i).concat(rows.slice(i+1)); setRows(next); onChange(next) }

  return (
    <div>
      <div className="toolbar" style={{ justifyContent: 'space-between' }}>
        <h4 className="section-title" style={{ margin: 0 }}>{label}</h4>
        <button className="btn secondary" onClick={addRow}>Add</button>
      </div>
      <div style={{ display: 'grid', gap: 8 }}>
        {rows.map((v, i) => (
          <div key={i} className="row" style={{ gap: 8 }}>
            <input placeholder={placeholder} value={v} onChange={e => update(i, e.target.value)} />
            <button className="btn ghost" onClick={() => removeRow(i)}>Remove</button>
          </div>
        ))}
      </div>
    </div>
  )
}


