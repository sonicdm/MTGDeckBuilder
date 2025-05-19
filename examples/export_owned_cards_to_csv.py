import csv
import os
from mtg_deck_builder.db.setup import setup_database
from mtg_deck_builder.db.repository import InventoryRepository

def export_owned_cards_to_csv(db_url, output_csv):
    from sqlalchemy.orm import sessionmaker
    engine = setup_database(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    inventory_repo = InventoryRepository(session)
    owned_cards = inventory_repo.get_owned_cards()

    with open(output_csv, "w", newline='', encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Card Name", "Quantity"])
        for item in owned_cards:
            writer.writerow([item.card_name, item.quantity])

    session.close()
    engine.dispose()
    print(f"Exported {len(owned_cards)} owned cards to {output_csv}")

if __name__ == "__main__":
    # Adjust these paths as needed
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "profile_cards.db"))
    db_url = f"sqlite:///{db_path}"
    output_csv = os.path.abspath(os.path.join(os.path.dirname(__file__), "owned_cards.csv"))
    export_owned_cards_to_csv(db_url, output_csv)
