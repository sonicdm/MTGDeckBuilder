# loads the AtomicCards json data and creates a new AtomicCards object
import json
from typing import List

from pydantic import ValidationError

from mtg_deck_builder.models.cards import AtomicCards, AtomicCard
from mtg_deck_builder.models.inventory import Inventory, InventoryItem

import json
from mtg_deck_builder.models.cards import AtomicCard

import json
from typing import Dict, Any
from mtg_deck_builder.models.cards import AtomicCards, AtomicCard

import json
from typing import Dict, Any
from mtg_deck_builder.models.cards import AtomicCards, AtomicCard

import json
from typing import Dict
from mtg_deck_builder.models.cards import AtomicCards, AtomicCard

BASIC_LAND_NAMES = {"Plains", "Island", "Swamp", "Mountain", "Forest"}

def load_atomic_cards_from_json(json_file_path: str) -> AtomicCards:
    """
    Loads an AtomicCards object from a JSON file where some card entries may be arrays.
    For basic lands, we unify them into a single dictionary entry named exactly
    'Mountain', 'Plains', etc., ignoring multiple prints.

    For non-lands:
      - If 'details' is a list of length N, we parse each item as a separate card
        with the suffix (variant i+1).

    If it's a single dict, parse it as a single card with the original name.
    """
    with open(json_file_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    data = raw_data.get("data", {})
    if not isinstance(data, dict):
        raise ValueError(f"Top-level 'data' is not a dict in {json_file_path}")

    final_cards: Dict[str, AtomicCard] = {}

    for name, details in data.items():
        if name in BASIC_LAND_NAMES:
            # This is a basic land.
            # If details is a list, we pick the first item or unify them.
            # We'll just pick the first if it's an array:
            if isinstance(details, list) and len(details) > 0:
                # details[0] must be a dict
                if not isinstance(details[0], dict):
                    raise TypeError(f"Basic land '{name}' array item is not a dict: {details[0]}")
                # parse the first item
                card_obj = AtomicCard(**details[0])
            elif isinstance(details, dict):
                # normal single dict
                card_obj = AtomicCard(**details)
            else:
                raise TypeError(
                    f"Basic land '{name}' has invalid structure: {type(details)} => {details}"
                )

            # Store under the exact base name
            final_cards[name] = card_obj
            continue

        # Non-basic land logic:
        if isinstance(details, list):
            # multi-variant approach
            for i, variant_data in enumerate(details):
                if not isinstance(variant_data, dict):
                    raise TypeError(
                        f"Card '{name}' variant {i+1} is not a dict: {variant_data}"
                    )
                variant_name = f"{name} (variant {i+1})"
                card_obj = AtomicCard(**variant_data)
                final_cards[variant_name] = card_obj

        elif isinstance(details, dict):
            # Normal single card
            card_obj = AtomicCard(**details)
            final_cards[name] = card_obj
        else:
            raise TypeError(f"Card '{name}' has invalid type {type(details)} => {details}")

    return AtomicCards(**{"data": final_cards})




def load_inventory_from_txt(txt_file_path: str) -> Inventory:
    """
    Loads a card inventory from a text file where each line has the format:
    "<quantity> <card name>"

    e.g.:
        1 Lightning Bolt
        4 Evolving Wilds
        2 Goblin Arsonist

    If a line does not begin with a valid integer, we SKIP that line entirely.
    Returns an Inventory instance containing valid InventoryItems.
    """
    items: List[InventoryItem] = []

    with open(txt_file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue  # skip empty lines

            # Split on the first space
            parts = line.split(" ", 1)
            if len(parts) < 2:
                # Not enough tokens -> skip
                continue

            quantity_str, card_name = parts
            try:
                quantity_int = int(quantity_str)
            except ValueError:
                # If we can't parse an integer at the start, skip the line
                continue

            try:
                item = InventoryItem(card_name=card_name.strip(), quantity=quantity_int)
                items.append(item)
            except ValidationError as e:
                # If the item is invalid per Pydantic, skip it (or log the error)
                print(f"Skipping invalid line: '{line}'. Error: {e}")

    return Inventory(items=items)
