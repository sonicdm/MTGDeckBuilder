### this script will load my card inventory, load the atomic card data, and export the inventory with full card metadata
### All information on the card will be exported, including the card name, card type, card text, card mana cost, card power, card toughness, card rarity, card set, card color, card legal formats, and card image
### I will use the Inventory class to load my card inventory, the AtomicCard class to load the atomic card data, and the Collection class to export the inventory with full card metadata
### Z:\Scripts\MTGDecks\inventory_files\card_inventory_2025-03-14.txt
### Z:\Scripts\MTGDecks\atomic_json_files\AtomicCards.json
from mtg_deck_builder.models.inventory import Inventory
from mtg_deck_builder.models.cards import AtomicCard
from mtg_deck_builder.models.collection import Collection
from mtg_deck_builder.data_loader import load_atomic_cards_from_json, load_inventory_from_txt
import json

# Load my card inventory
inventory_path = r"Z:\Scripts\MTGDecks\inventory_files\card_inventory_2025-03-14.txt"
inventory = load_inventory_from_txt(inventory_path)

# Load the atomic card data
atomic_cards_path = r"Z:\Scripts\MTGDecks\atomic_json_files\AtomicCards.json"
atomic_cards = load_atomic_cards_from_json(atomic_cards_path)

# Export the inventory with full card metadata
collection = Collection.build_from_inventory(atomic_cards, inventory)

# Export the collection
# use only cards owned and have a quantity > 0 to filter the collection
owned_collection = collection.get_owned_cards_collection(min_qty=1)
standard_legal_owned_collection = owned_collection.filter_cards(legal_in=["Standard"])

# describe the collection structure for ChatGPT to interpret. It must be done manually as there is no function for expor or describe the collection structure

# Export the collection to a JSON file
# Pydantic models can be converted to dictionaries using the .model_dump()
collection_dict = standard_legal_owned_collection.model_dump()
output_path = r"full_card_metadata_collection.json"
with open(output_path, "w") as f:
    json.dump(collection_dict, f, indent=2)

print(f"Collection exported to: {output_path}")

# Inspect the collection object and related object and present a strong description of what the fields are.

# The collection object is a representation of the user's card collection with full card metadata. It contains the following fields:
# - cards: a dictionary mapping card names to CardInCollection objects. Each CardInCollection object contains the following fields:
#   - card: an AtomicCard object representing the card's metadata, including the card type, text, mana cost, power, toughness, rarity, set, color, legal formats, and image.
#   - quantity_owned: an integer representing the number of copies of the card owned by the user.
# - inventory: an Inventory object representing the user's inventory of cards. It contains a list of InventoryItem objects, each representing a card and its quantity.
# - total_owned: an integer representing the total number of owned cards in the collection, excluding basic lands.
# - owned_cards: a dictionary mapping card names to the quantity of owned cards in the collection, excluding basic lands and cards with zero quantity.
# - get_owned_cards_collection(min_qty): a method that returns a new Collection object containing only owned cards with a quantity greater than or equal to min_qty.
# The collection object provides a comprehensive view of the user's card collection, including detailed metadata for each card and inventory

# The AtomicCard object represents the metadata of a single Magic: The Gathering card. It contains the following fields:
# - name: a string representing the card's name.
# - type: a string representing the card's type (e.g., creature, instant, sorcery).
# - text: a string representing the card's text description.
# - mana_cost: a string representing the card's mana cost.
# - power: an integer representing the card's power (if applicable).
# - toughness: an integer representing the card's toughness (if applicable).
# - rarity: a string representing the card's rarity (e.g., common, uncommon, rare).
# - set: a string representing the card's set name.
# - color: a string representing the card's color identity.
# - legal_formats: a list of strings representing the legal formats in which the card is legal.
# - image: a string representing the URL of the card's image.
# The AtomicCard object provides detailed information about a specific Magic: The Gathering card, including its attributes, text, and image

# The Inventory object represents a user's inventory of Magic: The Gathering cards. It contains the following fields:
# - items: a list of InventoryItem objects, each representing a card and its quantity in the inventory.
# - to_dict(): a method that returns a dictionary mapping card names to quantities for non-basic cards in the inventory.
# - get_owned_quantity(card_name): a method that returns the quantity of a specific card owned by the user, treating basic lands as infinite.
# - filter_by_quantity(min_quantity): a method that returns a new Inventory object with only items that have at least min_quantity.
# The Inventory object provides functionality for managing and querying a user's inventory of Magic: The Gathering cards, including filtering and quantity calculations.

# The Collection object combines the AtomicCard and Inventory objects to represent a user's card collection with full card metadata. It contains the following fields:
# - cards: a dictionary mapping card names to CardInCollection objects. Each CardInCollection object contains an AtomicCard object and a quantity_owned field.
# - inventory: an Inventory object representing the user's inventory of cards.
# - total_owned: an integer representing the total number of owned cards in the collection, excluding basic lands.
# - owned_cards: a dictionary mapping card names to the quantity of owned cards in the collection, excluding basic lands and cards with zero quantity.
# - get_owned_cards_collection(min_qty): a method that returns a new Collection object containing only owned cards with a quantity greater than or equal to min_qty.
# The Collection object provides a comprehensive view of the user's card collection, combining detailed card metadata with inventory information.





