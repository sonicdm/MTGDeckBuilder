# collection.py

from typing import Dict
from pydantic import BaseModel, Field
from mtg_deck_builder.models.cards import AtomicCards
from mtg_deck_builder.models.inventory import Inventory

BASIC_LAND_NAMES = {"Plains", "Island", "Swamp", "Mountain", "Forest"}

class Collection(AtomicCards):
    """
    Subclass of AtomicCards that adds an 'owned_quantities' dict to track how many
    copies of each card the user owns, plus infinite basic lands if not in the inventory.
    This file omits placeholder filter/deck-building logic to keep it minimal and clear.
    """

    owned_quantities: Dict[str, int] = Field(default_factory=dict)

    class Config:
        # Pydantic v2 config to allow alias usage (AtomicCards often uses 'data' -> 'cards')
        allow_population_by_field_name = True

    @classmethod
    def build_from_inventory(
        cls,
        atomic_cards: AtomicCards,
        inventory: Inventory
    ) -> "Collection":
        """
        Creates a new Collection by merging the base AtomicCards data
        with the user's inventory. Basic lands are infinite.
        """
        # Convert the parent AtomicCards object to a dict with aliases
        parent_data = atomic_cards.model_dump(
            by_alias=True,
            exclude_unset=True
        )
        # Parse into a new Collection
        new_obj = cls.model_validate(parent_data)

        # Fill owned_quantities from the Inventory
        inv_dict = inventory.to_dict()  # e.g. {"Lightning Bolt": 4, ...}
        for card_name in new_obj.cards.keys():
            if card_name in BASIC_LAND_NAMES:
                new_obj.owned_quantities[card_name] = 999999  # infinite
            else:
                new_obj.owned_quantities[card_name] = inv_dict.get(card_name, 0)

        return new_obj

    def get_owned_quantity(self, card_name: str) -> int:
        """
        Returns how many copies of `card_name` are owned, or 999999 if it's a basic land.
        """
        return self.owned_quantities.get(card_name, 0)
