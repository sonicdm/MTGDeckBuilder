# Example: Building a Magic: The Gathering Deck from a YAML Profile

This example demonstrates how to use the `mtg_deck_builder` package to build a Magic: The Gathering deck from a YAML configuration file, using your own card database and inventory.

## Steps

1. **Set up file paths**
   - Specify the paths to your Scryfall AllPrintings JSON, your inventory file, and your YAML deck template.

2. **Bootstrap the database and inventory**
   - Use the `bootstrap` function to load card and set data, as well as your inventory, into a local SQLite database.

3. **Set up a database session**
   - Use `get_session` to create a SQLAlchemy session for database access.

4. **Create repository objects**
   - Use `CardRepository` and `InventoryRepository` to access cards and inventory from the database.

5. **Build a deck from the YAML template**
   - Use `build_deck_from_yaml` to select cards and quantities based on your YAML configuration.

6. **Print the deck list and statistics**
   - Print the deck list, a random opening hand, and various deck statistics (mana value, color balance, card types, ramp count, and MTG Arena import format).

7. **Clean up**
   - Close the database session.

---

## Example Code

```python
import os
from mtg_deck_builder.db.bootstrap import bootstrap
from mtg_deck_builder.db import get_session
from mtg_deck_builder.db.repository import CardRepository, InventoryRepository
from mtg_deck_builder.yaml_builder.yaml_deckbuilder import build_deck_from_yaml

# 1. Set up file paths (edit these as needed for your setup)
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "profile_cards.db"))
db_url = f"sqlite:///{db_path}"
all_printings_path = "AllPrintings.json"  # Scryfall AllPrintings.json file
inventory_path = "card inventory.txt"     # Your inventory file (plain text)
yaml_path = "yaml_test_template.yaml"     # Your deck YAML template

# 2. Bootstrap the card database and inventory
print("Bootstrapping card database and inventory...")
bootstrap(all_printings_path, inventory_path, db_url, use_tqdm=True)

# 3. Set up a SQLAlchemy session for database access
print("Setting up database session...")
session = get_session(db_url)

# 4. Create repository objects for cards and inventory
card_repo = CardRepository(session=session)
inventory_repo = InventoryRepository(session)

# 5. Build a deck from the YAML template
print("Building deck from YAML template...")
deck = build_deck_from_yaml(yaml_path, card_repo, inventory_repo=inventory_repo)
if deck is None:
    print("Deck build failed: build_deck_from_yaml returned None.")
    exit(1)

# 6. Print the deck list and statistics
print("\nDeck List:")
print("=" * 40)
for card in deck.cards.values():
    print(f"{card.name} | Mana Cost: {card.mana_cost} | Rarity: {card.rarity} | Colors: {', '.join(card.colors or ['C'])} | Qty: {card.owned_qty}")

print("\nDeck Statistics:")

print("Random Hand:")
hand = deck.sample_hand(7)
for card in hand:
    print(f"  {card.name} | Mana Cost: {card.mana_cost} | Rarity: {card.rarity} | Colors: {', '.join(card.colors or ['C'])} | Qty: {card.owned_qty}")

print("=" * 40)
print("Calculating average mana value...")
avg_mana_value = deck.average_mana_value()
print(f"Average Mana Value: {avg_mana_value:.2f}")

print("Calculating average power/toughness for creatures...")
avg_power, avg_toughness = deck.average_power_toughness()
print(f"Average Power/Toughness (creatures only): {avg_power:.2f}/{avg_toughness:.2f}")

print("Analyzing color balance...")
color_counts = deck.color_balance()
print("Color Balance:")
for color, count in color_counts.items():
    print(f"  {color}: {count}")

print("Counting card types...")
type_counts = deck.count_card_types()
print("Card Type Counts:")
for card_type, count in type_counts.items():
    print(f"  {card_type}: {count}")

print("Counting mana ramp spells...")
ramp_count = deck.count_mana_ramp()
print(f"Ramp Spells Count: {ramp_count}")

print("MTG Arena Import:")
print(deck.mtg_arena_import())

# 7. Clean up the session
session.close()
print("Session closed. Tutorial complete.")
```

---

## Notes
- Make sure you have the required files (`AllPrintings.json`, your inventory file, and your YAML template) in the correct locations.
- The YAML template should define your deck's configuration, categories, and constraints.
- The script will print a summary of your deck and statistics to the console.

---

For more details, see the documentation in the `mtg_deck_builder` package and the example YAML templates.

