\
from typing import Dict
from pydantic import BaseModel, Field

from mtg_deck_builder.models.cards import AtomicCards
from mtg_deck_builder.models.inventory import Inventory

BASIC_LAND_NAMES = {"Plains", "Island", "Swamp", "Mountain", "Forest"}

class Collection(AtomicCards):
    owned_quantities: Dict[str, int] = Field(default_factory=dict)

    class Config:
        allow_population_by_field_name = True

    @classmethod
    def build_from_inventory(cls, atomic_cards: AtomicCards, inventory: Inventory) -> "Collection":
        parent_data = atomic_cards.model_dump(by_alias=True, exclude_unset=True)
        new_obj = cls.model_validate(parent_data)

        inv_dict = inventory.to_dict()
        for card_name in new_obj.data.keys():
            if card_name in BASIC_LAND_NAMES:
                new_obj.owned_quantities[card_name] = 999999
            else:
                new_obj.owned_quantities[card_name] = inv_dict.get(card_name, 0)

        return new_obj

    def get_owned_quantity(self, card_name: str) -> int:
        return self.owned_quantities.get(card_name, 0)
