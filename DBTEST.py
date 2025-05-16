from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from mtg_deck_builder.db.repository import CardRepository, InventoryRepository, CardDB
from mtg_deck_builder.db.models import Base
from mtg_deck_builder.models.deck import Deck


def main():
    print("Step 1: Connecting to the database...")
    engine = create_engine("sqlite:///cards.db")
    Session = sessionmaker(bind=engine)
    session = Session()

    print("Step 2: Initializing repositories...")
    card_repo = CardRepository(session)
    inventory_repo = InventoryRepository(session)

    #filter whole collection instead of ownedL
    any_ub = card_repo.filter_cards(
        color_identity=["U", "B"],
        color_mode="subset",  # or "subset", "exact" depending on desired match style
        legal_in="standard"
    )
    print("Step 3: Fetching owned inventory items...")
    owned_items = inventory_repo.get_owned_cards()

    print("Step 4: Building repository of owned cards...")
    owned_card_repo = card_repo.get_owned_cards_by_inventory(owned_items)
    CardDB.bind_inventory(inventory_repo)

    print("Step 5: Filtering for UB Standard-legal cards...")
    ub_standard_cards: CardRepository = owned_card_repo.filter_cards(
        color_identity=["U", "B"],
        color_mode="subset",  # or "subset", "exact" depending on desired match style
        legal_in="standard"
    )

    print("Step 6: Constructing a deck from filtered cards...")
    deck = Deck.from_repo(ub_standard_cards, limit=60, random_cards=True)


    print("\nDeck List:")
    print("=" * 40)
    for card in deck.get_all_cards():
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

    print("Counting mana ramp spells...")
    ramp_count = deck.count_mana_ramp()
    print(f"Ramp Spells Count: {ramp_count}")

    pass  # breakpoint


if __name__ == "__main__":
    main()
