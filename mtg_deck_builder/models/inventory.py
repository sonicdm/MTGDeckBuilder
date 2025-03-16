# inventory.py
from typing import List, Dict
from pydantic import BaseModel, Field

BASIC_LAND_NAMES = {"Plains", "Island", "Swamp", "Mountain", "Forest"}

class InventoryItem(BaseModel):
    card_name: str
    quantity: int = 1

class Inventory(BaseModel):
    items: List[InventoryItem] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, int]:
        """
        Returns a dict mapping card_name -> quantity for nonbasic cards only.
        """
        mapping = {}
        for it in self.items:
            mapping[it.card_name] = mapping.get(it.card_name, 0) + it.quantity
        return mapping

    def get_owned_quantity(self, card_name: str) -> int:
        """
        Returns the quantity the user owns for a given card.
        If card_name is a basic land, returns a very large number (effectively infinite).
        """
        if card_name in BASIC_LAND_NAMES:
            return 999999  # effectively infinite
        # Otherwise, return the real quantity from items
        return self.to_dict().get(card_name, 0)

    def filter_by_quantity(self, min_quantity: int = 1) -> "Inventory":
        """
        Returns a new Inventory with only the items that have at least `min_quantity`.
        """
        new_items = [it for it in self.items if it.quantity >= min_quantity]
        return Inventory(items=new_items)

    def __iter__(self):
        return iter(self.items)
