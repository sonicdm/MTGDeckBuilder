import React from 'react'

export type PriorityCard = { name: string; min_copies: number }

type Props = {
  label?: string
  items: PriorityCard[]
  onChange: (items: PriorityCard[]) => void
}

export default function PriorityCardsTable({ label = 'Priority Cards', items, onChange }: Props) {
  const [rows, setRows] = React.useState<PriorityCard[]>(items || [])
  React.useEffect(() => { setRows(items || []) }, [JSON.stringify(items)])

  function update(i: number, patch: Partial<PriorityCard>) {
    const next = rows.slice()
    next[i] = { ...next[i], ...patch }
    setRows(next)
    onChange(next.filter(r => (r.name || '').trim()))
  }
  function addRow() { setRows(rows.concat([{ name: '', min_copies: 1 }])) }
  function removeRow(i: number) {
    const next = rows.slice(0, i).concat(rows.slice(i + 1))
    setRows(next)
    onChange(next)
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
            <input placeholder="Card name" value={r.name || ''} onChange={e => update(i, { name: e.target.value })} style={{ flex: 2 }} />
            <input type="number" min={1} placeholder="Qty" value={r.min_copies ?? 1} onChange={e => update(i, { min_copies: Math.max(1, Number(e.target.value||1)) })} style={{ width: 90 }} />
            <button className="btn ghost" onClick={() => removeRow(i)}>Remove</button>
          </div>
        ))}
      </div>
    </div>
  )
}


