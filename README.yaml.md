
# MTG YAML Deck Template Guide

This document explains the structure and options for the YAML deck templates used by the MTG deck builder tools.

---

## Top-Level Structure

```yaml
deck:
  name: "Deck Name"
  colors: ["B", "R"]           # List of deck colors (W, U, B, R, G, C)
  size: 60                     # Total deck size
  max_card_copies: 4           # Max copies per card (except basic lands)
  allow_colorless: true        # Allow colorless cards
  legalities: ["standard"]     # List of legal formats
  owned_cards_only: true       # Only use cards you own (from inventory)
  mana_curve:
    min: 1                     # Minimum CMC for included cards
    max: 5                     # Maximum CMC for included cards
  key_cards:
    weighting_rules:
      priority_text:
        # Use plain text or regex (surrounded by /.../) to boost scoring
        graveyard: 3
        /return.*graveyard.*battlefield/: 4
      rarity_bonus:
        rare: 2
        mythic: 3
      mana_penalty:
        threshold: 4
        penalty_per_point: 1
      min_score_to_flag: 5     # (Optional) Flag cards with high score

categories:
  creatures:
    target: 24
    preferred_keywords: ["lifelink", "menace"]
    priority_text: ["return", "dies", "mill"]
  removal:
    target: 8
    priority_text: ["destroy", "exile", "sacrifice"]
  card_draw:
    target: 4
    priority_text: ["draw", "mill"]
  graveyard_synergy:
    target: 6
    priority_text: ["graveyard", "return", "reanimate"]

card_constraints:
  avoid_cards_with_text:
    - "can't block"
    - "lose the game"

priority_cards:
  - name: "Gix's Command"
    min_copies: 1
  - name: "Massacre Girl, Known Killer"
    min_copies: 1

mana_base:
  land_count: 24
  special_lands:
    count: 5
    prefer: ["surveil", "scry", "{T}, Sacrifice", "return target", "graveyard", "{T}: Add {B} or"]
    avoid: ["enters the battlefield tapped", "{T}: Add {C}"]
  balance:
    adjust_by_mana_symbols: true

fallback_strategy:
  fill_with_any: true
```

---

## Section Details

### `deck`
- **name**: Deck name.
- **colors**: List of deck colors (W, U, B, R, G, C).
- **size**: Total number of cards in the deck.
- **max_card_copies**: Maximum allowed copies per card (except basic lands).
- **allow_colorless**: If true, allows colorless cards.
- **legalities**: List of formats (e.g., `standard`, `modern`).
- **owned_cards_only**: If true, only uses cards you own (from inventory).
- **mana_curve**: Restricts included cards by converted mana cost.
- **key_cards**: Scoring rules for prioritizing cards (see below).

### `categories`
Defines deck sections and how many cards to target for each.  
Each category can have:
- **target**: Number of cards to include.
- **preferred_keywords**: Keywords to prefer.
- **priority_text**: Text or regex patterns to prioritize.

### `card_constraints`
- **avoid_cards_with_text**: List of phrases to avoid in card text.

### `priority_cards`
List of cards to always include, with minimum copies.

### `mana_base`
- **land_count**: Total number of lands.
- **special_lands**: Preferences for non-basic lands.
- **balance**: If true, adjusts basic land distribution by mana symbols.

### `fallback_strategy`
- **fill_with_any**: If true, fills remaining slots with any legal cards.

---

## Key Card Weighting Rules

- **priority_text**:  
  - Key: Text or `/regex/` pattern to match in card text.
  - Value: Score bonus if matched.
- **rarity_bonus**:  
  - Key: Rarity (e.g., `rare`, `mythic`).
  - Value: Score bonus.
- **mana_penalty**:  
  - **threshold**: CMC above which penalty applies.
  - **penalty_per_point**: Penalty per CMC above threshold.
- **min_score_to_flag**:  
  - (Optional) If a card's score meets/exceeds this, it may be flagged as a "key card".

---

## Example

See `tests/sample_data/b-grave-recursion.yaml` for a full example.

---

## Notes

- Regex patterns for `priority_text` must start and end with `/`, e.g. `/return.*graveyard/`.
- All sections are optional except `deck`.
- The script will always ensure the correct number of lands and respect inventory if `owned_cards_only` is set.

