import os
import time
import json
import pickle
import csv

from mtg_deck_builder.models.inventory import Inventory
from mtg_deck_builder.models.cards import AtomicCard
from mtg_deck_builder.models.collection import Collection
from mtg_deck_builder.data_loader import load_atomic_cards_from_json, load_inventory_from_txt

INVENTORY_PATH = r"Z:\Scripts\MTGDecks\inventory_files\card inventory.txt"
ATOMIC_JSON_PATH = r"Z:\Scripts\MTGDecks\atomic_json_files\AtomicCards.json"
ATOMIC_PICKLE_PATH = r"Z:\Scripts\MTGDecks\atomic_json_files\AtomicCards.pickle"
COLLECTION_PICKLE_PATH = r"Z:\Scripts\MTGDecks\collection.pkl"
JSON_EXPORT_PATH = r"full_card_metadata_collection.json"
CSV_EXPORT_PATH = r"full_card_metadata_collection.csv"


def load_or_cache_atomic_cards():
    json_mtime = os.path.getmtime(ATOMIC_JSON_PATH)
    pickle_mtime = os.path.getmtime(ATOMIC_PICKLE_PATH) if os.path.exists(ATOMIC_PICKLE_PATH) else 0

    if pickle_mtime > json_mtime:
        with open(ATOMIC_PICKLE_PATH, "rb") as f:
            return pickle.load(f)

    cards = load_atomic_cards_from_json(ATOMIC_JSON_PATH)
    with open(ATOMIC_PICKLE_PATH, "wb") as f:
        pickle.dump(cards, f)
    return cards


def load_or_build_collection(atomic_cards, inventory):
    inventory_mtime = os.path.getmtime(INVENTORY_PATH)
    collection_mtime = os.path.getmtime(COLLECTION_PICKLE_PATH) if os.path.exists(COLLECTION_PICKLE_PATH) else 0

    if collection_mtime > inventory_mtime:
        with open(COLLECTION_PICKLE_PATH, "rb") as f:
            return pickle.load(f)

    collection = Collection.build_from_inventory(atomic_cards, inventory)
    with open(COLLECTION_PICKLE_PATH, "wb") as f:
        pickle.dump(collection, f)
    return collection


def export_collection_to_json(collection):
    with open(JSON_EXPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(collection.model_dump(), f, indent=2)
    print(f"Collection exported to: {JSON_EXPORT_PATH}")


def export_collection_to_csv(collection):
    headers = ["Name", "Type", "Power", "Toughness", "Mana Cost", "Colors", "Text", "Quantity", "Standard Legal"]
    with open(CSV_EXPORT_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for card in collection.cards.values():
            writer.writerow([
                card.name,
                card.type,
                card.power or "",
                card.toughness or "",
                card.manaCost,
                ",".join(card.colorIdentity),
                card.text,
                card.quantity,
                str(card.is_legal_in("Standard")),
            ])


if __name__ == "__main__":
    inventory = load_inventory_from_txt(INVENTORY_PATH)
    atomic_cards = load_or_cache_atomic_cards()
    collection = load_or_build_collection(atomic_cards, inventory)

    owned_cards = collection.get_owned_cards_collection(min_qty=1)
    standard_legal = owned_cards.filter_cards(legal_in=["Standard"], color_mode="only", color_identity=["G", "B"])

    export_collection_to_json(standard_legal)
    export_collection_to_csv(standard_legal)
