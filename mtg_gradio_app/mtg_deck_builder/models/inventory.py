\
from pydantic import BaseModel
from typing import List, Dict

class InventoryItem(BaseModel):
    card_name: str
    quantity: int

class Inventory(BaseModel):
    items: List[InventoryItem]

    def to_dict(self) -> Dict[str, int]:
        """
        Merge duplicates by name
        """
        merged = {}
        for it in self.items:
            merged[it.card_name] = merged.get(it.card_name, 0) + it.quantity
        return merged
