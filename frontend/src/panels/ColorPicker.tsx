import React from 'react'

type Props = {
  value: string[]
  onChange: (colors: string[]) => void
}

const COLOR_META: { code: string; name: string }[] = [
  { code: 'W', name: 'White' },
  { code: 'U', name: 'Blue' },
  { code: 'B', name: 'Black' },
  { code: 'R', name: 'Red' },
  { code: 'G', name: 'Green' },
  { code: 'C', name: 'Colorless' },
]

export default function ColorPicker({ value, onChange }: Props) {
  const selected = new Set((value || []).map((c) => c.toUpperCase()))

  function toggle(code: string) {
    const next = new Set(selected)
    if (next.has(code)) next.delete(code)
    else next.add(code)
    onChange(Array.from(next))
  }

  return (
    <div>
      <div className="section-title" style={{ marginBottom: 8 }}>Colors</div>
      <div className="color-row">
        {COLOR_META.map((c) => {
          const icon = c.code.toLowerCase()
          const iconClass = `ms ms-${icon} ms-cost`
          const checked = selected.has(c.code)
          return (
            <label key={c.code} className={`color-chip ${checked ? 'selected' : ''}`} title={c.name}>
              <input type="checkbox" checked={checked} onChange={() => toggle(c.code)} />
              <i className={iconClass} aria-hidden="true" />
              <span className="color-code">{c.code}</span>
            </label>
          )
        })}
      </div>
    </div>
  )
}


