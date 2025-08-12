import React from 'react'
import YAML from 'js-yaml'
import ListInput from './ListInput'
import KeyValueTable from './KeyValueTable'
import ArrayTable from './ArrayTable'
import ColorPicker from './ColorPicker'
import HelpTip from './HelpTip'
import PriorityCardsTable from './PriorityCardsTable'

type Props = {
  form: any
  setForm: (updater: (prev: any) => any) => void
  onYamlLoaded?: (text: string) => void
  onBuild?: () => Promise<void>
}

export default function BuilderForm({ form, setForm, onYamlLoaded, onBuild }: Props) {
  const [availableConfigs, setAvailableConfigs] = React.useState<string[]>([])
  const [selectedConfig, setSelectedConfig] = React.useState<string>("")
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

  function formToYaml() {}

  async function onUploadFile(_e: React.ChangeEvent<HTMLInputElement>) {}

  async function refreshConfigList() {
    const data = await fetch('/api/config/files').then(r => r.json())
    const files: string[] = [...(data.yaml || []), ...(data.json || [])]
    setAvailableConfigs(files)
  }

  React.useEffect(() => { refreshConfigList() }, [])

  async function loadSelectedConfig(path: string) {
    if (!path) return
    console.debug('[BuilderForm] loadSelectedConfig path:', path)
    const res = await fetch('/api/config/file?path=' + encodeURIComponent(path))
    if (!res.ok) return
    const body = await res.json()
    const text = body.text || ''
    console.debug('[BuilderForm] fetched length:', text.length)
    try { onYamlLoaded && onYamlLoaded(text); console.debug('[BuilderForm] onYamlLoaded called') } catch (e) { console.error(e) }
    try {
      const obj = YAML.load(text)
      console.debug('[BuilderForm] parsed keys:', obj && typeof obj === 'object' ? Object.keys(obj as any) : [])
      if (obj && typeof obj === 'object') {
        // Normalize minimal shape expected by form
        const next: any = {
          deck: { name: '', colors: [], size: 60, max_card_copies: 4, legalities: [], ...(obj as any).deck },
          categories: (obj as any).categories || {},
          mana_base: { land_count: 24, ...((obj as any).mana_base || {}) },
          card_constraints: (obj as any).card_constraints || {},
          priority_cards: (obj as any).priority_cards || [],
          scoring_rules: (obj as any).scoring_rules || {},
          fallback_strategy: (obj as any).fallback_strategy || {},
        }
        console.debug('[BuilderForm] normalized deck:', next.deck)
        setForm(() => next)
      }
    } catch (e) {
      // Ignore parse errors; YAML editor still populated
      console.error('[BuilderForm] YAML parse error:', e)
    }
  }

  async function saveYamlToConfigs() {}

  return (
    <div className="row">
      <div className="col panel" style={{ flex: 1.2 }}>
        <h3 className="section-title">Config form</h3>
        <div className="hint">Start by selecting an existing config or enter details below. Click Build to preview the deck; Save YAML stores the config in data/configs.</div>
        <div className="toolbar" style={{ marginTop: 8 }}>
          <button className="btn" onClick={onBuild}>Build</button>
        </div>
        <div className="toolbar" style={{ marginBottom: 8 }}>
          <select value={selectedConfig} onChange={e => { setSelectedConfig(e.target.value); loadSelectedConfig(e.target.value) }}>
            <option value="">Select existing config</option>
            {availableConfigs.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <button className="btn secondary" onClick={refreshConfigList}>Refresh</button>
        </div>
        <div style={{ display: 'grid', gap: 8 }}>
          <label>
            <span className="help"><HelpTip text="Give your deck a descriptive name. This will appear in exports and listings." /> Deck Name</span>
            <input placeholder="e.g., Gruul Stomp" value={form.deck.name || ''} onChange={e => updateForm('deck.name', e.target.value)} />
            <div className="hint">A friendly name for this deck configuration.</div>
          </label>
          <ColorPicker value={form.deck.colors || []} onChange={vals => updateForm('deck.colors', vals)} />
          <label>
            <span className="help"><HelpTip text="Total number of cards to build towards. Common sizes: 60 for Constructed, 100 for Commander." /> Deck Size</span>
            <input type="number" value={form.deck.size || 60} onChange={e => updateForm('deck.size', Number(e.target.value))} />
            <div className="hint">Typical sizes: 60 (Constructed), 100 (Commander).</div>
          </label>
          <label>
            <span className="help"><HelpTip text="Maximum copies of the same card (by name) allowed. Commander: 1." /> Max Copies</span>
            <input type="number" value={form.deck.max_card_copies || 4} onChange={e => updateForm('deck.max_card_copies', Number(e.target.value))} />
            <div className="hint">Set the duplicate limit per card (Commander is usually 1).</div>
          </label>
          <ListInput label="Legalities" values={form.deck.legalities || []} onChange={vals => updateForm('deck.legalities', vals)} placeholder="standard, historic" />
          <label>
            <span className="help"><HelpTip text="Target total lands in the deck. Adjust after setting colors and curve." /> Lands</span>
            <input type="number" value={form.mana_base?.land_count || 24} onChange={e => updateForm('mana_base.land_count', Number(e.target.value))} />
            <div className="hint">Total lands target. Adjust after choosing colors and curve.</div>
          </label>
        </div>

        {/* left column ends with basics only */}
      </div>
      <div className="col panel" style={{ flex: 1.8 }}>
        <h3 className="section-title">Categories <HelpTip text="Define role buckets for the builder: creatures, removal, card_draw, buffs, etc. Each category can specify: a target number of cards; keywords and text snippets to prefer; and basic types to prioritize (e.g., instant, creature). The builder will try to hit these targets before fallback logic."></HelpTip></h3>
        <div className="hint">Examples: creatures (28), removal (6), card_draw (3). Add keys below, then tune each.</div>
        <ArrayTable label="Category Keys" items={Object.keys(form.categories || {})} onChange={(keys) => {
          const next: any = {}
          for (const k of keys) next[k] = form.categories?.[k] || { target: 0, preferred_keywords: [], priority_text: [], preferred_basic_type_priority: [] }
          updateForm('categories', next)
        }} />
        {Object.entries(form.categories || {}).map(([k, v]: any) => (
          <div key={k} className="panel" style={{ marginTop: 8 }}>
            <div className="toolbar">
              <strong>{k}</strong>
              <HelpTip text="Set a target count and guide selection with keywords, text snippets, and preferred types." />
            </div>
            <label>
              Target
              <input type="number" value={v.target || 0} onChange={e => updateForm(`categories.${k}.target`, Number(e.target.value))} />
            </label>
            <ListInput label="Preferred Keywords" values={v.preferred_keywords || []} onChange={vals => updateForm(`categories.${k}.preferred_keywords`, vals)} />
            <ListInput label="Priority Text" values={v.priority_text || []} onChange={vals => updateForm(`categories.${k}.priority_text`, vals)} />
            <ListInput label="Basic Type Priority" values={v.preferred_basic_type_priority || []} onChange={vals => updateForm(`categories.${k}.preferred_basic_type_priority`, vals)} />
          </div>
        ))}

        <div className="panel" style={{ marginTop: 12 }}>
          <h3 className="section-title">Priority Cards <HelpTip text="Force-include specific cards by name with a minimum quantity. These are inserted first, respecting Max Copies and legality."></HelpTip></h3>
          <div className="hint">Use the table to add card names and quantities.</div>
          <PriorityCardsTable
            items={form.priority_cards || []}
            onChange={(list) => updateForm('priority_cards', list)}
          />
        </div>

        <div className="panel" style={{ marginTop: 12 }}>
          <h3 className="section-title">Scoring Rules <HelpTip text="Tune how cards are ranked during selection. Higher weights are more preferred. Combine keyword abilities, actions, text matches, and type bonuses for nuanced behavior."></HelpTip></h3>
          <div className="hint">Tip: keep weights small (1–3) and iterate.</div>
          <KeyValueTable label="Keyword Abilities" data={form.scoring_rules?.keyword_abilities || {}} onChange={obj => updateForm('scoring_rules.keyword_abilities', obj)} />
          <KeyValueTable label="Keyword Actions" data={form.scoring_rules?.keyword_actions || {}} onChange={obj => updateForm('scoring_rules.keyword_actions', obj)} />
          <KeyValueTable label="Ability Words" data={form.scoring_rules?.ability_words || {}} onChange={obj => updateForm('scoring_rules.ability_words', obj)} />
          <KeyValueTable label="Text Matches" data={form.scoring_rules?.text_matches || {}} onChange={obj => updateForm('scoring_rules.text_matches', obj)} />
          <div className="panel" style={{ marginTop: 8 }}>
            <h4 className="section-title">Type Bonus</h4>
            <KeyValueTable label="Basic Types" data={form.scoring_rules?.type_bonus?.basic_types || {}} onChange={obj => updateForm('scoring_rules.type_bonus.basic_types', obj)} />
            <KeyValueTable label="Sub Types" data={form.scoring_rules?.type_bonus?.sub_types || {}} onChange={obj => updateForm('scoring_rules.type_bonus.sub_types', obj)} />
            <KeyValueTable label="Super Types" data={form.scoring_rules?.type_bonus?.super_types || {}} onChange={obj => updateForm('scoring_rules.type_bonus.super_types', obj)} />
          </div>
          <KeyValueTable label="Rarity Bonus" data={form.scoring_rules?.rarity_bonus || {}} onChange={obj => updateForm('scoring_rules.rarity_bonus', obj)} />
          <div className="row" style={{ gap: 8 }}>
            <label style={{ flex: 1 }}>
              Mana Penalty Threshold
              <input type="number" value={form.scoring_rules?.mana_penalty?.threshold || 5} onChange={e => updateForm('scoring_rules.mana_penalty.threshold', Number(e.target.value))} />
            </label>
            <label style={{ flex: 1 }}>
              Penalty Per Point
              <input type="number" value={form.scoring_rules?.mana_penalty?.penalty_per_point || 1} onChange={e => updateForm('scoring_rules.mana_penalty.penalty_per_point', Number(e.target.value))} />
            </label>
          </div>
          <label>
            Min Score To Flag
            <input type="number" value={form.scoring_rules?.min_score_to_flag || 0} onChange={e => updateForm('scoring_rules.min_score_to_flag', Number(e.target.value))} />
          </label>
        </div>

        <div className="panel" style={{ marginTop: 12 }}>
          <h3 className="section-title">Card Constraints <HelpTip text="Apply global rules before scoring. Rarity boosts gently bias selection; excluded keywords hard-filter cards."></HelpTip></h3>
          <div className="hint">Example exclude: defender, hexproof, lifelink (for aggro).</div>
          <div className="row" style={{ gap: 8 }}>
            <KeyValueTable label="Rarity Boost" data={form.card_constraints?.rarity_boost || {}} onChange={obj => updateForm('card_constraints.rarity_boost', obj)} />
          </div>
          <ListInput label="Exclude Keywords" values={form.card_constraints?.exclude_keywords || []} onChange={vals => updateForm('card_constraints.exclude_keywords', vals)} />
        </div>

        <div className="panel" style={{ marginTop: 12 }}>
          <h3 className="section-title">Fallback Strategy <HelpTip text="How to fill remaining slots when targets aren’t satisfied."></HelpTip></h3>
          <div className="hint">How to fill remaining slots if targets aren’t met.</div>
          <label>
            Fill with any
            <input type="checkbox" checked={!!form.fallback_strategy?.fill_with_any} onChange={e => updateForm('fallback_strategy.fill_with_any', e.target.checked)} />
          </label>
          <ListInput label="Fill Priority" values={form.fallback_strategy?.fill_priority || []} onChange={vals => updateForm('fallback_strategy.fill_priority', vals)} />
          <label>
            Allow less than target
            <input type="checkbox" checked={!!form.fallback_strategy?.allow_less_than_target} onChange={e => updateForm('fallback_strategy.allow_less_than_target', e.target.checked)} />
          </label>
        </div>
      </div>
    </div>
  )
}


