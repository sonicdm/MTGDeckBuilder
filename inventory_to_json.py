#!/usr/bin/env python3
import json
import argparse
import sys

# Adjust these imports to match your project structure:
from mtg_deck_builder.data_loader import (
    load_inventory_from_txt,
    load_atomic_cards_from_json
)
from mtg_deck_builder.models.inventory import Inventory
from mtg_deck_builder.models.collection import Collection

def export_detailed_inventory(inventory: Inventory, collection: Collection) -> dict:
    """
    Merges the user's inventory with the atomic card data from 'collection',
    returning a dictionary structure with a list of cards under 'inventory'.
    Instead of picking individual fields, we do a model_dump() on each AtomicCard
    so we get all fields automatically.
    """
    inv_dict = inventory.to_dict()  # e.g. {"Lightning Bolt": 4, ...}

    detailed_list = []
    for card_name, qty in inv_dict.items():
        card_obj = collection.cards.get(card_name)
        if card_obj:
            # Dump the entire Pydantic model as a dict
            card_data = card_obj.model_dump()
            # Add your 'quantity' and 'cardName' fields
            card_data["quantity"] = qty
            card_data["cardName"] = card_obj.name
            detailed_list.append(card_data)
        else:
            # Card not found in atomic data => minimal info
            detailed_list.append({
                "cardName": card_name,
                "quantity": qty
            })

    return {"inventory": detailed_list}

def main():
    parser = argparse.ArgumentParser(
        description="Export a detailed JSON of your inventory, merging with atomic card data."
    )
    parser.add_argument("--inventory", required=True, help="Path to inventory .txt file")
    parser.add_argument("--atomic", required=True, help="Path to atomic .json file")
    parser.add_argument("--output", required=True, help="Path to output .json file")

    args = parser.parse_args()

    # 1) Load the inventory
    inventory = load_inventory_from_txt(args.inventory)

    # 2) Load atomic data
    atomic_cards = load_atomic_cards_from_json(args.atomic)

    # 3) Build a Collection to unify data
    collection = Collection.build_from_inventory(atomic_cards, inventory)

    # 4) Merge & export
    export_data = export_detailed_inventory(inventory, collection)

    # 5) Write to the output file
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)

    print(f"Exported detailed inventory to {args.output}")

if __name__ == "__main__":
    sys.exit(main())
