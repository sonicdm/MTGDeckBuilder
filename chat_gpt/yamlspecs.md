Here’s a detailed **`yamlspec.md`** file describing the YAML schema used for deck configurations in your MTG Deckbuilder project. This will serve as the authoritative reference for developers, testers, or AI agents working with the configuration format.

---

````markdown
# MTG Deckbuilder - YAML Specification

This document defines the complete structure and expected values for a deck configuration YAML used in the MTG Deckbuilder system.

---

## Top-Level Keys

### `deck` (required)
Defines core identity and deck construction rules.

```yaml
deck:
  name: "Deck Name"
  colors: ["R", "G"]
  size: 60
  max_card_copies: 4
  allow_colorless: true
  legalities: ["standard"]
  owned_cards_only: true
  color_match_mode: "subset"  # Options: subset, exact, inclusive
  mana_curve:
    min: 1
    max: 8
    curve_shape: "bell"
    curve_slope: "up"
````

---

### `categories` (optional)

Declares the desired role distribution (e.g. creature count) and card preferences.

```yaml
categories:
  creatures:
    target: 24
    preferred_keywords: ["Haste", "Trample"]
    priority_text: ["Aggressive", "Attacks each turn"]
  removal:
    target: 6
    priority_text: ["Destroy", "Exile"]
  buffs:
    target: 4
    priority_text: ["Pump", "+X/+X"]
```

Common categories: `creatures`, `removal`, `card_draw`, `buffs`, `utility`

---

### `priority_cards` (optional)

Specifies must-include cards with minimum copy counts.

```yaml
priority_cards:
  - name: "Fatal Push"
    min_copies: 2
  - name: "Tenacious Underdog"
    min_copies: 3
```

---

### `mana_base` (optional)

Manages land count and optimization preferences.

```yaml
mana_base:
  land_count: 22
  special_lands:
    count: 6
    prefer: ["Add {B}", "Untapped"]
    avoid: ["Deals damage to you"]
  balance:
    adjust_by_mana_symbols: true
```

---

### `card_constraints` (optional)

Controls what to avoid and prioritizes rarity.

```yaml
card_constraints:
  exclude_keywords: ["Defender"]
  rarity_boost:
    common: 0
    uncommon: 0
    rare: 1
    mythic: 1
```

---

### `fallback_strategy` (optional)

Specifies what to do if categories can’t be fully satisfied.

```yaml
fallback_strategy:
  fill_with_any: true
  fill_priority: ["creatures", "removal"]
  allow_less_than_target: false
```

---

### `scoring_rules` (optional)

Advanced logic to fine-tune how cards are evaluated.

```yaml
scoring_rules:
  priority_text:
    "Draw a card": 2
    "Impulsive draw": 1
  rarity_bonus:
    common: 0
    uncommon: 1
    rare: 2
    mythic: 3
  mana_penalty:
    threshold: 5
    penalty_per_point: 2
  min_score_to_flag: 5
```

---

## Notes

* All sections are merged into a single DeckConfig object at runtime.
* All values are validated via Pydantic on load.
* YAML comments (`#`) are allowed and encouraged for human readability.
* Undefined fields are ignored with a warning.

---

## Example Minimal YAML

```yaml
deck:
  name: "Mono-Black GY Recursion"
  colors: ["B"]
  size: 60
  max_card_copies: 4
  legalities: ["standard"]
  owned_cards_only: true
  allow_colorless: true
```

```

Would you like me to save this into `mtg_deckbuilder_ui/docs/yamlspec.md` or output it as a file now?
```
