from collections import defaultdict
from typing import Dict, Optional, Any, Union, List
from pydantic import BaseModel, Field, field_validator

from mtg_deck_builder.models.cards import AtomicCard

BASIC_LAND_NAMES = {"Plains", "Island", "Swamp", "Mountain", "Forest"}

class InventoryItem(BaseModel):
    card_name: str
    quantity: Optional[int] = Field(default=1, ge=0)
    is_infinite: bool = Field(default=False)

    @classmethod
    def create(cls, card_name: str, quantity: Optional[int] = 1):
        """
        Creates an InventoryItem, ensuring proper handling of basic lands.
        """
        if not isinstance(quantity, (int, type(None))):
            raise ValueError("Quantity must be an integer or None")
        is_infinite = card_name in BASIC_LAND_NAMES
        return cls(
            card_name=card_name,
            quantity=None if is_infinite else max(0, quantity or 0),
            is_infinite=is_infinite,
        )

    def __eq__(self, other):
        if not isinstance(other, InventoryItem):
            return False
        return self.model_dump() == other.model_dump()

class Inventory(BaseModel):
    items: Union[Dict[str, InventoryItem],InventoryItem] = Field(default_factory=dict)

    @field_validator("items", mode="before")
    @classmethod
    def validate_items(cls, v: Any):
        if isinstance(v, list):
            raise ValueError("items must be a dictionary, but received a list.")
        if not isinstance(v, dict):
            raise ValueError("items must be a dictionary mapping card names to InventoryItem objects.")
        return v

    def to_dict(self, include_infinite=False) -> Dict[str, int]:
        """
        Returns a dict mapping card_name -> quantity. Can include/exclude infinite cards.
        """
        return {
            name: (None if item.is_infinite else item.quantity)
            for name, item in self.items.items()
            if include_infinite or not item.is_infinite
        }

    def get_owned_quantity(self, card_name: str) -> Optional[int]:
        """
        Returns the quantity owned for a given card. If it's a basic land, return None (infinite).
        """
        item = self.items.get(card_name)
        if item is None:
            return 0  # Card not in inventory
        return None if item.is_infinite else item.quantity

    def add_card(self, card_name: str, quantity: int = 1):
        """
        Adds cards to the inventory, updating quantity if the card already exists.
        """
        if card_name in self.items:
            if not self.items[card_name].is_infinite:
                self.items[card_name].quantity += quantity
        else:
            self.items[card_name] = InventoryItem.create(card_name, quantity)

    def remove_card(self, card_name: str, quantity: int = 1):
        """
        Removes a specified quantity of a card from the inventory. If the quantity reaches 0, remove the card.
        """
        if card_name in self.items and not self.items[card_name].is_infinite:
            self.items[card_name].quantity = max(0, self.items[card_name].quantity - quantity)
            if self.items[card_name].quantity == 0:
                del self.items[card_name]  # Remove the card entirely if quantity is 0

    @classmethod
    def from_dict(cls, card_list: Dict[str,int]) -> "Inventory":
        """
        Creates an Inventory from a dict of card names and quantities.
        """
        items = {name: InventoryItem.create(name, quantity) for name, quantity in card_list.items()}
        return cls(items=items)


    @classmethod
    def from_list(cls, card_list: List[InventoryItem]) -> "Inventory":
        """
        Creates an Inventory from a list of card names.
        """
        items = defaultdict()
        for item in card_list:
            card_name = item.card_name
            if card_name in items:
                if not items[card_name].is_infinite:
                    items[card_name].quantity += item.quantity
            else:
                items[card_name] = item

        return cls(items=items)


    def __eq__(self, other):
        if not isinstance(other, Inventory):
            return False
        return self.items == other.items

    def __repr__(self):
        displayed_items = list(self.items.values())[:5]  # Limit to 5 items for readability
        formatted_items = ", ".join(f"{item.card_name} ({item.quantity if item.quantity is not None else '∞'})" for item in displayed_items)
        remaining_count = max(0, len(self.items) - 5)
        return f"Inventory([{formatted_items}{', ...' if remaining_count > 0 else ''}] {remaining_count} more)"