from mtg_deck_builder.models.collection import Collection
from mtg_deck_builder.data_loader import load_inventory_from_txt, load_atomic_cards_from_json
from tests.helpers import get_sample_data_path
import json

gruul_cards = get_sample_data_path("gruul_deck_example.txt")
azorius_cards = get_sample_data_path("azorius_deck_example.txt")
combined_decks = get_sample_data_path("incompatible_decks_combined.txt")
full_atomic_cards_json = get_sample_data_path("AtomicCards.json")
atomic_cards = load_atomic_cards_from_json(full_atomic_cards_json)
gruul_inventory = load_inventory_from_txt(gruul_cards)
azorius_inventory = load_inventory_from_txt(azorius_cards)
combined_inventory = load_inventory_from_txt(combined_decks)
gruul_collection = Collection.build_from_inventory(atomic_cards, gruul_inventory, only_owned=True)
azorius_collection = Collection.build_from_inventory(atomic_cards, azorius_inventory, only_owned=True)
combined_collection = Collection.build_from_inventory(atomic_cards, combined_inventory, only_owned=True)

# combined dump to json
with open("combined_collections_dump.json", "w") as f:
    json.dump(combined_collection.model_dump(), f, indent=4)
# gruul dump to json
with open("gruul_collections_dump.json", "w") as f:
    json.dump(gruul_collection.model_dump(), f, indent=4)

# azorius dump to json
with open("azorius_collections_dump.json", "w") as f:
    json.dump(azorius_collection.model_dump(), f, indent=4)

pass
