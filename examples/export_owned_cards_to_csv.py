import csv
import os

from mtg_deck_builder.db.bootstrap import bootstrap
from mtg_deck_builder.db.repository import SummaryCardRepository
from mtg_deck_builder.db.setup import setup_database


def export_owned_cards_to_csv(db_url, output_csv):
    from sqlalchemy.orm import sessionmaker
    inventory_file = r"Z:\Scripts\MTGDecks\inventory_files\card inventory.txt"
    all_printings_path = r"Z:\Scripts\MTGDecks\MTG_json_files\AllPrintings.json"
    bootstrap(all_printings_path, inventory_file, db_url, use_tqdm=True)
    engine = setup_database(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    card_repo = SummaryCardRepository(session=session)
    # Get cards with inventory quantity >= 1
    owned_repo = card_repo.filter_by_inventory_quantity(min_quantity=1)
    # filter by color identity
    ub_repo = owned_repo.filter_cards(color_identity=["U", "B", "R"], color_mode="subset", legal_in=["alchemy"])
    # export repo to csv

    with open(output_csv, mode='w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['name', 'rarity', 'color_identity', 'owned_qty', 'text', 'mana_cost']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for card in ub_repo.get_all_cards():
            writer.writerow({
                'name': card.name,
                'rarity': card.rarity,
                'color_identity': card.colors,
                'owned_qty': card.owned_qty,
                'text': card.text,
                'mana_cost': card.mana_cost,
            })


if __name__ == "__main__":
    # Adjust these paths as needed
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "profile_cards.db"))
    db_url = f"sqlite:///{db_path}"
    output_csv = os.path.abspath(os.path.join(os.path.dirname(__file__), "owned_cards.csv"))
    export_owned_cards_to_csv(db_url, output_csv)
