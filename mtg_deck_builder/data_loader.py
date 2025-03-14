# data_loader.py
import json
from typing import List, Dict
from pydantic import ValidationError

from mtg_deck_builder.models.cards import AtomicCards, AtomicCard
from mtg_deck_builder.models.inventory import Inventory, InventoryItem

BASIC_LAND_NAMES = {"Plains", "Island", "Swamp", "Mountain", "Forest"}


def load_atomic_cards_from_json(json_file_path: str) -> AtomicCards:
    """
    Loads an AtomicCards object from a JSON file where some card entries may be arrays.

    For basic lands:
      - If it's a list, we pick the first item or unify them.
        We store them under the exact base name (e.g. "Mountain").

    For non-basic lands or other cards:
      - If 'details' is a list of length 1, we flatten it to the base name (no "(variant 1)").
      - If 'details' is a list of length > 1, we do (variant i+1).
      - If it's a dict, we store it under the base name directly.
    """
    with open(json_file_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    data = raw_data.get("data", {})
    if not isinstance(data, dict):
        raise ValueError(f"Top-level 'data' is not a dict in {json_file_path}")

    final_cards: Dict[str, AtomicCard] = {}

    for name, details in data.items():
        # 1) Basic lands logic
        if name in BASIC_LAND_NAMES:
            if isinstance(details, list) and len(details) > 0:
                # If it's an array, pick the first
                if not isinstance(details[0], dict):
                    raise TypeError(f"Basic land '{name}' array item is not a dict: {details[0]}")
                card_obj = AtomicCard(**details[0])
            elif isinstance(details, dict):
                card_obj = AtomicCard(**details)
            else:
                raise TypeError(f"Basic land '{name}' has invalid structure => {details}")

            final_cards[name] = card_obj
            continue

        # 2) Non-basic logic
        if isinstance(details, list):
            if len(details) == 1:
                # Flatten single array to base name
                single_obj = details[0]
                if not isinstance(single_obj, dict):
                    raise TypeError(f"Card '{name}' single array item not a dict => {single_obj}")
                card_obj = AtomicCard(**single_obj)
                final_cards[name] = card_obj
            else:
                # multiple prints/faces => use (variant X)
                for i, variant_data in enumerate(details):
                    if not isinstance(variant_data, dict):
                        raise TypeError(
                            f"Card '{name}' variant {i + 1} is not a dict: {variant_data}"
                        )
                    variant_name = f"{name} (variant {i + 1})"
                    card_obj = AtomicCard(**variant_data)
                    final_cards[variant_name] = card_obj

        elif isinstance(details, dict):
            # Normal single card
            card_obj = AtomicCard(**details)
            final_cards[name] = card_obj
        else:
            raise TypeError(f"Card '{name}' has invalid type => {type(details)} => {details}")

    return AtomicCards(**{"data": final_cards})


def load_inventory_from_txt(txt_file_path: str) -> Inventory:
    """
    Loads a card inventory from a text file where each line has the format:
    "<quantity> <card name>"

    If a line does not begin with a valid integer, we SKIP that line entirely.
    Returns an Inventory instance containing valid InventoryItems.
    """
    items: List[InventoryItem] = []

    with open(txt_file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue  # skip empty lines

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
                print(f"Skipping invalid line: '{line}'. Error: {e}")

    return Inventory(items=items)
