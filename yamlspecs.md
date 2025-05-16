# **MTG YAML Deck Configuration Guide**

This guide explains how to structure a YAML file to define deck constraints and categorization for Magic: The Gathering decks.

---

## **General Deck Structure**
```yaml
deck:
  name: "Deck Name"
  colors: ["W", "U", "B", "R", "G"]  # Use mana symbols: W=White, U=Blue, B=Black, R=Red, G=Green
  size: 60  # Default for Standard format
  max_card_copies: 4  # Maximum copies of non-basic cards
  allow_colorless: true  # If colorless cards are allowed
  legalities: ["standard", "modern", "commander"]  # Format restrictions
```
- **`name`**: The deck's name.
- **`colors`**: The deck’s allowed colors.
- **`size`**: Total deck size (typically 60 for Standard, 100 for Commander).
- **`max_card_copies`**: The maximum copies of a card (usually 4 in Standard).
- **`allow_colorless`**: Whether colorless cards are permitted.
- **`legalities`**: Formats the deck must comply with.

---

## **Mana Base Configuration**
```yaml
mana_base:
  land_count: 24
  special_lands:
    count: 6
    prefer:
      - "Fetch land"
      - "Shock land"
      - "Dual land"
      - "Mana-fixing"
    avoid:
      - "Enters tapped"
      - "Pain lands"
  balance:
    adjust_by_mana_symbols: true  # Adjust land ratio based on mana symbols in deck
```
- **`land_count`**: Total number of lands.
- **`special_lands`**:
  - **`count`**: How many non-basic lands to include.
  - **`prefer`**: Keywords to prioritize in land selection.
  - **`avoid`**: Keywords to avoid in land selection.
- **`balance.adjust_by_mana_symbols`**: Automatically adjusts land distribution based on spell costs.

---

## **Card Categories**
Each deck will categorize cards based on their roles.

```yaml
categories:
  creatures:
    target: 22
    preferred_keywords: ["Haste", "Trample"]
    priority_text: ["Aggressive", "Deals damage", "Attacks each turn"]
  removal:
    target: 8
    priority_text: ["Destroy", "Exile", "Deal damage"]
  card_draw:
    target: 4
    priority_text: ["Draw a card", "Impulse draw"]
  buffs:
    target: 4
    priority_text: ["+X/+X until end of turn", "Give haste or trample"]
```

### **Standard Categories**
#### 1️⃣ **Creatures**
- **Description**: Units used to attack and defend.
- **Detection**: Identified by "Creature" type.
- **Preferred Keywords**:
  - **Aggro decks**: "Haste", "Trample", "First strike"
  - **Midrange decks**: "Flying", "Lifelink", "Indestructible"
  - **Control decks**: "Defender", "Hexproof"

#### 2️⃣ **Removal**
- **Description**: Spells that remove threats.
- **Detection**: Cards with "Destroy", "Exile", "Sacrifice".
- **Preferred Types**:
  - **Single Target**: "Destroy target creature"
  - **Mass Removal**: "Each creature", "All creatures"

#### 3️⃣ **Burn**
- **Description**: Damage-dealing spells.
- **Detection**: "Deal X damage".
- **Preferred Keywords**:
  - **Direct damage**: "Deal damage to any target"
  - **Creature-focused**: "Deal damage to target creature"

#### 4️⃣ **Card Draw**
- **Description**: Increases hand size for more options.
- **Detection**: "Draw a card", "Look at the top X cards".
- **Preferred Types**:
  - **Instant-speed**: "Draw X cards"
  - **Impulse Draw**: "Exile the top card and play it this turn"

#### 5️⃣ **Ramp**
- **Description**: Provides extra mana for future turns.
- **Detection**: "Add mana", "Search your library for a land".
- **Preferred Types**:
  - **Land Ramp**: "Search for a land and put it onto the battlefield"
  - **Mana Dorks**: "Add mana to your mana pool"

#### 6️⃣ **Buffs & Combat Tricks**
- **Description**: Temporary or permanent stat boosts.
- **Detection**: "+X/+X until end of turn", "Gain haste or trample".
- **Preferred Types**:
  - **Pump Spells**: "Target creature gets +X/+X"
  - **Evasion Boosts**: "Target creature gains flying"

#### 7️⃣ **Counters**
- **Description**: Stops opponent's spells from resolving.
- **Detection**: "Counter target spell".
- **Preferred Types**:
  - **Hard Counters**: "Counter target spell"
  - **Soft Counters**: "Counter unless they pay X"

#### 8️⃣ **Graveyard Synergy**
- **Description**: Cards that interact with the graveyard.
- **Detection**: "Return target card from your graveyard".
- **Preferred Types**:
  - **Reanimation**: "Put target creature from graveyard onto battlefield"
  - **Self-Mill**: "Put the top X cards into your graveyard"

#### 9️⃣ **Landfall Synergy**
- **Description**: Triggers when lands enter.
- **Detection**: "Whenever a land enters the battlefield".
- **Preferred Types**:
  - **Extra Land Drops**: "Play an additional land"
  - **Creature Buffs**: "Whenever a land enters, put a +1/+1 counter"

---

## **Card Constraints**
These define **filters** for automatic deck selection.

```yaml
card_constraints:
  rarity_boost:
    rare: 2  # Slightly prioritize rare cards
    mythic: 3  # Prefer mythics
  exclude_keywords: ["Defender", "Indestructible"]
  prefer_cards_with_text:
    - "Haste"
    - "Trample"
    - "Whenever you cast"
  avoid_cards_with_text:
    - "Counter target spell"
    - "Discard a card"
```

### **Constraint Options**
- **`rarity_boost`**: Weight for higher rarity cards.
- **`exclude_keywords`**: Avoids cards with specific abilities.
- **`prefer_cards_with_text`**: Prioritizes cards with matching phrases.
- **`avoid_cards_with_text`**: Avoids cards with unwanted effects.

---

## **Example Deck YAML for Gruul Aggro**
```yaml
deck:
  name: "Gruul Aggro"
  colors: ["R", "G"]
  size: 60
  max_card_copies: 4
  allow_colorless: false
  legalities: ["standard"]

mana_base:
  land_count: 24
  special_lands:
    count: 4
    prefer:
      - "Fetch land"
      - "Dual land"
    avoid:
      - "Enters tapped"
  balance:
    adjust_by_mana_symbols: true

categories:
  creatures:
    target: 22
    preferred_keywords: ["Haste", "Trample"]
    priority_text: ["Aggressive", "Deals damage", "Attacks each turn"]
  removal:
    target: 8
    priority_text: ["Destroy", "Exile", "Deal damage"]
  burn:
    target: 6
    priority_text: ["Deal damage to any target", "Instant-speed burn"]
  buffs:
    target: 4
    priority_text: ["+X/+X until end of turn", "Give haste or trample"]

card_constraints:
  rarity_boost:
    rare: 2
    mythic: 3
  exclude_keywords: ["Defender"]
  prefer_cards_with_text:
    - "Haste"
    - "Trample"
  avoid_cards_with_text:
    - "Counter target spell"
    - "Discard a card"
```

---

### **Final Notes**
- Adjust **targets** to fit your deck's game plan.
- Use **priority text** and **keywords** to guide automatic deck-building.
- Modify **land ratios** based on **mana symbols** in the deck.