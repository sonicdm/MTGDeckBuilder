import cProfile
import pstats
import os
import logging

from mtg_deck_builder.yaml_deck_builder import load_yaml_template, build_deck_from_yaml  # build_deck_from_yaml now orchestrates helpers
from mtg_deck_builder.db.setup import setup_database
from mtg_deck_builder.db.repository import CardRepository, InventoryRepository
from mtg_deck_builder.db.bootstrap import bootstrap

def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    logger = logging.getLogger(__name__)

    # Paths (adjust as needed)
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "profile_cards.db"))
    db_url = f"sqlite:///{db_path}"
    all_printings_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "atomic_json_files/AllPrintings.json"))
    inventory_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "inventory_files/card inventory.txt"))
    yaml_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "tests/sample_data/b-grave-recursion.yaml"))

    logger.debug(f"DB path: {db_path}")
    logger.debug(f"DB URL: {db_url}")
    logger.debug(f"AllPrintings path: {all_printings_path}")
    logger.debug(f"Inventory path: {inventory_path}")
    logger.debug(f"YAML path: {yaml_path}")

    # Bootstrap DB if needed
    if not os.path.exists(db_path):
        logger.info("[PROFILE] Bootstrapping database...")
        bootstrap(json_path=all_printings_path, inventory_path=inventory_path, db_url=db_url, use_tqdm=False)
    else:
        logger.debug("Database already exists, skipping bootstrap.")

    # Setup DB and session
    logger.debug("Setting up database engine and session.")
    engine = setup_database(db_url)
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    session = Session()

    # Load YAML and build deck
    logger.info("[PROFILE] Loading YAML template and building deck from YAML...")
    yaml_data = load_yaml_template(yaml_path)
    card_repo = CardRepository(session=session)
    inventory_repo = InventoryRepository(session)
    logger.debug("Repositories initialized.")
    logger.info("[PROFILE] Building deck from YAML...")
    deck = build_deck_from_yaml(yaml_data, card_repo, inventory_repo=inventory_repo)  # refactored, but call unchanged
    if deck is None:
        logger.error("[PROFILE] Deck build failed: build_deck_from_yaml returned None.")
        return
    logger.info(f"[PROFILE] Deck built with {sum(card.owned_qty for card in deck.cards.values())} cards.")

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


    session.close()
    engine.dispose()
    logger.debug("Session closed and engine disposed.")




if __name__ == "__main__":
    cProfile.run('main()', 'profile_stats.profile')
    print("[PROFILE] Profiling complete. Use pstats or snakeviz to analyze 'profile_stats'.")
    # Example: python -m pstats profile_stats
    # Or:     snakeviz profile_stats
