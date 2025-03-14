# logic/inventory_logic.py

from typing import List, Dict, Tuple
from mtg_deck_builder.models.collection import Collection

def build_inventory_list(
    collection: Collection,
    only_owned: bool = False
) -> Tuple[List[Dict[str, str]], int]:
    """
    Returns (rows, non_land_count).
    rows is a list of dict: {
      "card_name": str,
      "title_text": str,   # plain text for the 'title' attribute
      "owned": str,
      "is_land": bool
    }
    non_land_count is the total number of non-land cards in the final filtered set.
    """
    rows = []
    non_land_count = 0

    for card_name, card_obj in collection.cards.items():
        owned = collection.get_owned_quantity(card_name)
        if only_owned and owned <= 0:
            continue

        # Check if it's a land (a simple approach: if "Land" in card_obj.type)
        is_land = False
        if card_obj.type and "Land" in card_obj.type:
            is_land = True

        # We'll only increment non_land_count if not a land
        if not is_land:
            non_land_count += 1

        # Build plain text for the tooltip
        # Use \n for newlines, which we can convert to &#10; in the UI
        lines = [
            f"{card_obj.name}",
            f"Type: {card_obj.type or ''}",
            f"Mana Value: {card_obj.manaValue or 0}",
            f"Owned: {owned}",
        ]
        title_text = "\n".join(lines)

        rows.append({
            "card_name": card_name,
            "title_text": title_text,
            "owned": str(owned),
            "is_land": is_land,
        })

    return rows, non_land_count
