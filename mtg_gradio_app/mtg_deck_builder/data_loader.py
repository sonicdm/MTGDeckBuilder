\
import json
from mtg_deck_builder.models.cards import AtomicCards, AtomicCard
from typing import Dict

def load_atomic_cards_from_json(json_file_path: str) -> AtomicCards:
    with open(json_file_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    data = raw_data.get("data", {})
    if not isinstance(data, dict):
        raise ValueError(f"Top-level 'data' is not a dict in {json_file_path}")

    # For now, we assume no auto-fixing. If multi-variant, we store them with suffix (variant).
    cards: Dict[str, AtomicCard] = {}
    for name, details in data.items():
        if isinstance(details, list):
            for i, variant_data in enumerate(details):
                variant_name = f"{name} (variant {i+1})"
                card_obj = AtomicCard(**variant_data)
                cards[variant_name] = card_obj
        elif isinstance(details, dict):
            card_obj = AtomicCard(**details)
            cards[name] = card_obj
        else:
            raise TypeError(f"Card '{name}' has invalid structure => {details}")

    return AtomicCards(**{"data": cards})

def load_inventory_from_txt(txt_file_path: str):
    from mtg_deck_builder.models.inventory import Inventory, InventoryItem
    items = []
    with open(txt_file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(" ", 1)
            if len(parts) < 2:
                # skip
                continue
            qty_str, card_name = parts
            try:
                qty = int(qty_str)
            except ValueError:
                continue
            items.append(InventoryItem(card_name=card_name.strip(), quantity=qty))
    return Inventory(items=items)
