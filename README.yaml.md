# 🧾 MTG YAML Deck Template Guide

**(Categorized Keywords & Unified Scoring Edition)**

This guide defines the structure and behavior of a complete MTG deck configuration for automated deck building and scoring. It supports filtering, prioritization, keyword-aware evaluation, and owned-card legality.

---

## 🔷 1. `deck` – Core Deck Settings

```yaml
deck:
  name: "Deck Name"
  colors: ["B", "R"]
  color_match_mode: "subset"          # Options: exact, subset, any
  size: 60
  max_card_copies: 4
  allow_colorless: true
  legalities: ["alchemy"]
  owned_cards_only: true
  mana_curve:
    min: 1
    max: 5
    curve_shape: "bell"               # Options: bell, linear, flat
    curve_slope: "down"               # Options: up, down, flat
```

---

## 🧩 2. `priority_cards` – Must-Include Cards

```yaml
priority_cards:
  - name: "Alesha's Legacy"
    min_copies: 4
```

---

## 🌍 3. `mana_base` – Land Preferences & Balancing

```yaml
mana_base:
  land_count: 24
  special_lands:
    count: 6
    prefer: ["add {b}", "add {r}", "any color"]
    avoid: ["enters tapped unless"]
  balance:
    adjust_by_mana_symbols: true
```

---

## 🧠 4. `categories` – Role-Based Card Targets

```yaml
categories:
  creatures:
    target: 26
    preferred_keywords: ["haste", "menace", "first strike", "double strike"]
    priority_text: ["when this creature attacks", "sacrifice a creature", "/strike/"]
    preferred_basic_type_priority: ["creature", "planeswalker"]

  removal:
    target: 6
    priority_text: ["damage", "destroy", "/-x/-x/", "sacrifice another creature"]
    preferred_basic_type_priority: ["instant", "sorcery", "enchantment"]

  card_draw:
    target: 2
    priority_text: ["draw a card", "loot", "when this dies"]
    preferred_basic_type_priority: ["instant", "sorcery", "enchantment", "creature"]

  buffs:
    target: 4
    priority_text: ["+x/+0", "until end of turn", "double strike"]
    preferred_basic_type_priority: ["instant", "sorcery", "enchantment", "creature"]

  utility:
    target: 2
    priority_text: ["treasure", "scry", "return target creature card"]
    preferred_basic_type_priority: ["instant", "sorcery", "enchantment", "creature"]
```

> 💡 The `preferred_basic_type_priority` parameter is used to prioritize cards of certain basic types (e.g., 'creature', 'instant', 'sorcery', 'enchantment', 'planeswalker') when filling each category. This helps in selecting cards that better fit the intended role of the category.

---

## 🚫 5. `card_constraints` – Inclusion & Filtering

```yaml
card_constraints:
  rarity_boost:
    common: 1
    uncommon: 2
    rare: 2
    mythic: 1

  exclude_keywords: ["defender", "lifelink", "hexproof"]
```

---

## 🎯 6. `scoring_rules` – Unified and Categorized Evaluation

```yaml
scoring_rules:
  keyword_abilities:
    haste: 2
    menace: 2
    hexproof: -5
    deathtouch: 1
    flying: 1

  keyword_actions:
    scry: 1
    fight: 2
    exile: 3
    create: 2

  ability_words:
    raid: 2
    landfall: 1

  text_matches:
    "mobilize": 4
    "create a 1/1": 3
    "when this creature attacks": 2
    "/warrior/": 2
    "/sacrifice a creature/": 1

  type_bonus:
    basic_types:
      creature: 2
    sub_types:
      warrior: 3
      cleric: 1
    super_types:
      legendary: 1

  rarity_bonus:
    rare: 2
    mythic: 1

  mana_penalty:
    threshold: 5
    penalty_per_point: 1

  min_score_to_flag: 6
```

> 💡 All keywords are matched from card metadata fields — not just raw rules text. Case is normalized to lowercase.

---

## 🛠 7. `fallback_strategy` – Final Fill Logic

```yaml
fallback_strategy:
  fill_with_any: true
  fill_priority: ["creatures", "removal", "buffs"]
  allow_less_than_target: false
```

---

## 📌 Notes

* All keyword matches (`keyword_abilities`, `keyword_actions`, `ability_words`) are based on your structured metadata (e.g., `Keywords.json`).
* `priority_text` and `text_matches` allow both exact strings and regex (wrapped in `/.../`).
* All text is compared in `.lower()` form.
* Scoring is flat additive — no weights or multipliers.