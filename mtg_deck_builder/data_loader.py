# data_loader.py
import json
from collections import defaultdict
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

    - Deduplicates cards: If a card appears multiple times, the total is combined.
    - Caps any card's total quantity at 4.
    - Skips lines that do not start with a valid integer.
    - Skips lines where the card name is empty.

    Args:
        txt_file_path (str): The path to the inventory text file.

    Returns:
        Inventory: An instance of the Inventory class containing valid InventoryItems.
    """
    card_counts = defaultdict(int)  # Dictionary to store card counts (name -> quantity)

    try:
        with open(txt_file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue  # Skip empty lines

                parts = line.split(" ", 1)
                if len(parts) < 2:
                    continue  # Skip if no card name is present

                quantity_str, card_name = parts
                card_name = card_name.strip()

                try:
                    quantity_int = int(quantity_str)
                except ValueError:
                    continue  # Skip lines that don't start with an integer

                if not card_name:
                    continue  # Skip if card name is empty

                # Add to dictionary (deduplicate), but cap at 4
                card_counts[card_name] = min(4, card_counts[card_name] + quantity_int)

    except FileNotFoundError:
        print(f"Error: File '{txt_file_path}' not found.")
        return Inventory(items=[])  # Return an empty inventory

    # Convert dictionary to InventoryItems
    items = []
    for card_name, quantity in card_counts.items():
        try:
            item = InventoryItem(card_name=card_name, quantity=quantity)
            items.append(item)
        except ValidationError as e:
            print(f"Skipping invalid card '{card_name}' due to error: {e}")

    return Inventory(items=items)
