# MTG YAML Deck Template Guide

This document explains the structure and options for the YAML deck templates used by the MTG deck builder tools.

---

## Top-Level Structure

```yaml
deck:
  name: "Deck Name"                  # The name of the deck
  colors: ["B", "R"]                 # List of deck colors (W, U, B, R, G, C)
  color_match_mode: "subset"         # How strictly to match the color identity (exact, subset, any)
  size: 60                            # Total deck size
  max_card_copies: 4                  # Max copies per card (except basic lands)
  allow_colorless: true               # Allow colorless cards
  legalities: ["standard"]           # List of legal formats
  owned_cards_only: true              # Only use cards you own (from inventory)
  mana_curve:
    min: 1                            # Minimum CMC for included cards
    max: 5                            # Maximum CMC for included cards
    curve_shape: "bell"              # Shape of the mana curve, e.g., "bell", "linear"
    curve_slope: "up"                # Slope of the curve, e.g., "up", "down", "flat"

priority_cards:                       # Cards you'd strongly prefer to include
  - name: "Lightning Bolt"
    min_copies: 2
  - name: "Monastery Swiftspear"
    min_copies: 4

mana_base:
  land_count: 22                      # Total number of lands
  special_lands:
    count: 6
    prefer: ["Add {R} or {G}", "Untapped", "Mana fixing", "Gain life"]
    avoid: ["Enters tapped unless", "Deals damage to you"]
  balance:
    adjust_by_mana_symbols: true      # Adjust basic land distribution by mana symbols

categories:
  creatures:
    target: 24
    preferred_keywords: ["Haste", "Trample", "Menace"]
    priority_text: ["Aggressive", "Attacks each turn", /deal[s]? damage/]  # Each entry can be plain text or /regex/
  removal:
    target: 6
    priority_text: ["Destroy", "Exile", "Deal damage", "Fight"]  # Each entry can be plain text or /regex/
  card_draw:
    target: 4
    priority_text: ["Draw a card", "Impulse draw"]  # Each entry can be plain text or /regex/
  buffs:
    target: 4
    priority_text: ["+X/+0", "Until end of turn", "Give haste", "Pump spell"]  # Each entry can be plain text or /regex/
  utility:
    target: 2
    priority_text: ["Treasure", "Scry", "Loot", "Double strike"]  # Each entry can be plain text or /regex/

card_constraints:
  rarity_boost:
    common: 0                        # Weight for common cards
    uncommon: 0                      # Weight for uncommon cards
    rare: 2                          # Weight for rare cards
    mythic: 1                        # Weight for mythic cards
  exclude_keywords: ["Defender", "Cannot attack"]   # Hard exclusion, never include

scoring_rules:
  priority_text:
    "Aggressive": 2  # Key can be plain text or /regex/
    "Haste": 2
    /deal[s]? damage/: 3
  rarity_bonus:
    rare: 2
    mythic: 1
  mana_penalty:
    threshold: 5
    penalty_per_point: 1
  min_score_to_flag: 5

fallback_strategy:
  fill_with_any: true
  fill_priority: [creatures, removal, buffs]
  allow_less_than_target: false
```

---

## Section Details

### `deck`
- **name**: Deck name.
- **colors**: List of deck colors (W, U, B, R, G, C).
- **color_match_mode**: How strictly to match the color identity. Options: "exact", "subset", "any".
- **size**: Total number of cards in the deck.
- **max_card_copies**: Maximum allowed copies per card (except basic lands).
- **allow_colorless**: If true, allows colorless cards.
- **legalities**: List of formats (e.g., `standard`, `modern`).
- **owned_cards_only**: If true, only uses cards you own (from inventory).
- **mana_curve**: Restricts included cards by converted mana cost and curve shape.

### `priority_cards`
List of cards to always include, with minimum copies.
- **name**: Card name.
- **min_copies**: Minimum number of copies to include.

### `mana_base`
- **land_count**: Total number of lands.
- **special_lands**: Preferences for non-basic lands.
  - **count**: Number of special lands to include.
  - **prefer**: List of text/keywords to prefer in special lands.
  - **avoid**: List of text/keywords to avoid in special lands.
- **balance**: If true, adjusts basic land distribution by mana symbols.

### `categories`
Defines deck sections and how many cards to target for each.
Each category can have:
- **target**: Number of cards to include.
- **preferred_keywords**: Keywords to prefer.
- **priority_text**: Text or regex patterns to prioritize. Each entry can be plain text or `/regex/`.

### `card_constraints`
- **rarity_boost**: Weighting system for card rarity. Higher weights increase the likelihood of including cards of that rarity.
  - **common**: Weight for common cards.
  - **uncommon**: Weight for uncommon cards.
  - **rare**: Weight for rare cards.
  - **mythic**: Weight for mythic cards.
- **exclude_keywords**: List of phrases to never include in card text (hard exclusion).

### `scoring_rules`
- **priority_text**:  
  - Key: Text or `/regex/` pattern to match in card text.  
  - Value: Score bonus if matched. Each key can be plain text or `/regex/`.
- **rarity_bonus**:  
  - Key: Rarity (e.g., `rare`, `mythic`).  
  - Value: Score bonus.
- **mana_penalty**:  
  - **threshold**: CMC above which penalty applies.  
  - **penalty_per_point**: Penalty per CMC above threshold.
- **min_score_to_flag**:  
  - (Optional) If a card's score meets/exceeds this, it may be flagged as a "key card".

### `fallback_strategy`
- **fill_with_any**: If true, fills remaining slots with any legal cards.
- **fill_priority**: Order of categories to fill in preference if targets are unmet.
- **allow_less_than_target**: If false, must meet exact counts or skip.

---

## Notes

- Regex patterns for `priority_text` must start and end with `/`, e.g. `/deal[s]? damage/`.
- All sections except `deck` are optional, but recommended for best results.
- The script will always ensure the correct number of lands and respect inventory if `owned_cards_only` is set.
- `prefer_cards_with_text` and `avoid_cards_with_text` are omitted in favor of the more flexible `scoring_rules`.
