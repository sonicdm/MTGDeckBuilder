"""
Tutorial: Build a Magic: The Gathering deck from a YAML profile

This script demonstrates how to use the mtg_deck_builder package to:
  1. Bootstrap a card database and inventory from Scryfall JSON and a text file
  2. Set up a database session
  3. Load a deck configuration from a YAML template
  4. Build a deck using the deck builder modules
  5. Print the deck list and various deck statistics

Adjust the file paths below to match your environment and data files.
"""
from mtg_deck_builder.db import get_session
from mtg_deck_builder.db.bootstrap import bootstrap
from mtg_deck_builder.db.repository import CardRepository, InventoryRepository
from mtg_deck_builder.yaml_builder.yaml_deckbuilder import build_deck_from_yaml

# 1. Set up file paths (edit these as needed for your setup)
db_path = "profile_cards.db"
db_url = f"sqlite:///{db_path}"
all_printings_path = "AllPrintings.json"  # MTGJson AllPrintings.json file
inventory_path = "card inventory.txt"  # Your inventory file (plain text) MTG Arena Format
yaml_path = "yaml_test_template.yaml"  # Your deck YAML template

# 2. Bootstrap the card database and inventory
#    This loads card/set data and inventory into the database if not already present.
print("Bootstrapping card database and inventory...")
bootstrap(all_printings_path, inventory_path, db_url, use_tqdm=True)

# 3. Set up a SQLAlchemy session for database access
print("Setting up database session...")
with get_session(db_url) as session:
    # 4. Create repository objects for cards and inventory
    card_repo = CardRepository(session=session)
    inventory_repo = InventoryRepository(session)

    # 5. Build a deck from the YAML template
    #    This uses your deck builder logic to select cards and quantities based on the YAML config.
    print("Building deck from YAML template...")
    deck = build_deck_from_yaml(yaml_path, card_repo=card_repo, inventory_repo=inventory_repo)
    if deck is None:
        print("Deck build failed: build_deck_from_yaml returned None.")
        exit(1)

    # 6. Print the deck list and statistics
    print("\nDeck List:")
    print("=" * 40)
    for card in deck.cards.values():
        print(
            f"{card.name} | Mana Cost: {card.mana_cost} | Rarity: {card.rarity} | Colors: {', '.join(card.colors or ['C'])} | Qty: {card.owned_qty}")

    print("\nDeck Statistics:")

    # Draw a random opening hand
    print("Random Hand:")
    hand = deck.sample_hand(7)
    for card in hand:
        print(
            f"  {card.name} | Mana Cost: {card.mana_cost} | Rarity: {card.rarity} | Colors: {', '.join(card.colors or ['C'])} | Qty: {card.owned_qty}")

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

print("Session closed. Tutorial complete.")
