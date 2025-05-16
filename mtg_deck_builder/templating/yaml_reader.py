import yaml
from typing import Dict, List

from mtg_deck_builder.data_loader import load_inventory_from_txt, load_atomic_cards_from_json
from mtg_deck_builder.models.inventory import Inventory
from mtg_deck_builder.models.collection import Collection


def load_yaml_deck(file_path: str) -> Dict:
    """Loads deck-building criteria from a YAML file."""
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)





# # Usage
# yaml_criteria = load_yaml_deck('dmir.yaml')
# inventory = load_inventory('card_inventory_2025-03-14.txt')
# atomic_cards = load_atomic_cards_from_json('cards.json')
# collection = Collection.build_from_inventory(atomic_cards, inventory)
# filtered_collection = filter_collection_for_deck(collection, yaml_criteria)
# deck = build_deck(filtered_collection, yaml_criteria)
#
# # Print deck composition
# for card in deck:
#     print(f"{card.name} ({card.quantity}x)")
