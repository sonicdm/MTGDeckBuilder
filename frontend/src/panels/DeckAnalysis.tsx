import React from 'react'

type Row = { qty: number; name: string; type: string; mv: number }

type Props = { decklist?: Row[]; analysis?: any }

export default function DeckAnalysis({ decklist = [], analysis }: Props) {
  const mvCounts = React.useMemo(() => {
    if (analysis?.mana_curve && typeof analysis.mana_curve === 'object') {
      // Normalize keys (may arrive as strings) to numbers 0..7
      const out: Record<number, number> = {}
      for (const [k, v] of Object.entries(analysis.mana_curve as Record<string, any>)) {
        const numK = Math.min(7, Math.max(0, Number(k) || 0))
        out[numK] = Number(v) || 0
      }
      return out
    }
    const map: Record<number, number> = {}
    for (const r of decklist) {
      const mvNum = Math.round(Number(r.mv) || 0)
      // Exclude lands only when they have no mana value (true 0 MV lands)
      const isLand = String(r.type || '').toLowerCase().includes('land')
      if (isLand && mvNum === 0) continue
      const mv = Math.min(7, Math.max(0, mvNum))
      map[mv] = (map[mv] || 0) + r.qty
    }
    return map
  }, [analysis, decklist])

  const max = Math.max(1, ...Object.values(mvCounts))
  const bars = Array.from({ length: 8 }, (_, mv) => ({ mv, count: mvCounts[mv] || 0 }))

  const typeCounts = React.useMemo(() => {
    if (analysis?.type_counts && typeof analysis.type_counts === 'object') {
      return Object.entries(analysis.type_counts as Record<string, number>).sort((a, b) => b[1] - a[1])
    }
    const map: Record<string, number> = {}
    for (const r of decklist) {
      const t = (r.type || '').split(' — ')[0] || 'Other'
      map[t] = (map[t] || 0) + r.qty
    }
    return Object.entries(map).sort((a, b) => b[1] - a[1])
  }, [analysis, decklist])

  const colorBalance = React.useMemo(() => {
    return analysis?.color_balance || {}
  }, [analysis])

  const rarity = React.useMemo(() => {
    return analysis?.rarity_breakdown || {}
  }, [analysis])

  return (
    <div className="panel">
      <h3 className="section-title">Deck Analysis</h3>
      {analysis && (
        <div className="metrics-grid" style={{ marginBottom: 12 }}>
          <div className="metric"><div className="label">Total Cards</div><div className="value">{analysis.total_cards ?? decklist.reduce((s, r) => s + r.qty, 0)}</div></div>
          <div className="metric"><div className="label">Lands</div><div className="value">{analysis.land_count ?? decklist.filter(r => String(r.type||'').toLowerCase().includes('land')).reduce((s, r) => s + r.qty, 0)}</div></div>
          <div className="metric"><div className="label">Avg MV</div><div className="value">{analysis.avg_mana_value?.toFixed?.(2) ?? '-'}</div></div>
          <div className="metric"><div className="label">Synergy</div><div className="value">{analysis.synergy ?? '-'}</div></div>
        </div>
      )}
      <div className="row" style={{ gap: 16 }}>
        <div className="col" style={{ flex: 1 }}>
          <div className="row" style={{ justifyContent: 'space-between', alignItems: 'baseline' }}>
            <h4 className="section-title" style={{ margin: 0 }}>Mana Curve</h4>
            <span className="hint">Bars show card count per mana value (MV)</span>
          </div>
          <div style={{ border: '1px solid #1f2937', borderRadius: 8, padding: 8 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(8, 1fr)', gap: 8, alignItems: 'end', height: 160 }}>
              {bars.map(({ mv, count }) => (
                <div key={mv} style={{ position: 'relative', background: '#60a5fa', height: `${(count / max) * 100}%`, borderRadius: 4 }}>
                  <span style={{ position: 'absolute', top: -18, left: '50%', transform: 'translateX(-50%)', fontSize: 12 }}>{count}</span>
                </div>
              ))}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(8, 1fr)', gap: 8, marginTop: 6, fontSize: 12, color: 'var(--muted)' }}>
              {bars.map(({ mv }) => (<span key={mv} style={{ textAlign: 'center' }}>{mv === 7 ? '7+' : mv}</span>))}
            </div>
            <div className="hint">Legend: Blue bars = total cards</div>
          </div>
        </div>
        <div className="col" style={{ flex: 1 }}>
          <h4 className="section-title">Types</h4>
          <div style={{ border: '1px solid #1f2937', borderRadius: 8, padding: 8, maxHeight: 160, overflow: 'auto' }}>
            {typeCounts.map(([t, c]) => (
              <div key={t} className="row" style={{ justifyContent: 'space-between' }}>
                <span>{t}</span>
                <span>{c}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="row" style={{ gap: 16, marginTop: 12 }}>
        <div className="col" style={{ flex: 1 }}>
          <h4 className="section-title">Color Balance</h4>
          <div style={{ border: '1px solid #1f2937', borderRadius: 8, padding: 8 }}>
            {Object.entries(colorBalance).map(([k, v]: any) => {
              const icon = String(k || '').toLowerCase()
              const cls = `ms ms-${icon} ms-cost`
              return (
              <div key={k} className="row" style={{ gap: 8, alignItems: 'center' }}>
                <i className={cls} aria-hidden="true" />
                <div style={{ background: '#334155', height: 8, borderRadius: 4, flex: 1, position: 'relative' }}>
                  <div style={{ background: '#22c55e', width: `${Math.min(100, Number(v) || 0)}%`, height: '100%', borderRadius: 4 }} />
                </div>
                <span>{v}</span>
              </div>)
            })}
          </div>
        </div>
        <div className="col" style={{ flex: 1 }}>
          <h4 className="section-title">Rarity</h4>
          <div style={{ border: '1px solid #1f2937', borderRadius: 8, padding: 8 }}>
            {Object.entries(rarity).map(([k, v]: any) => (
              <div key={k} className="row" style={{ justifyContent: 'space-between' }}>
                <span>{k}</span>
                <span>{v}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}


