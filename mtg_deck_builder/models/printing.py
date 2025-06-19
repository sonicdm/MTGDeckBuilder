"""
A pydantic model representation of a MTGJSONCard for fixed copies of a card returned from the database.
takes a MTGJSONCard and returns a Printing object.
"""
from typing import List
from pydantic import BaseModel

from mtg_deck_builder.db.mtgjson_models.cards import MTGJSONCard

class Printing(BaseModel):
    """
    A pydantic model representation of a MTGJSONCard for fixed copies of a card returned from the database.
    fields mirror the fields of a MTGJSONCard, but are not required.
    """
    name: str
    quantity: int
    mana_cost: str
    converted_mana_cost: int
    type: str
    power: str
    toughness: str
    text: str
    rarity: str
    colors: List[str]


def from_mtgjson_card(card: MTGJSONCard) -> Printing:
    """
    Convert a MTGJSONCard to a Printing object.
    """
    return Printing(
        name=getattr(card, "name", ""),
        quantity=getattr(card, "quantity", 1),
        mana_cost=getattr(card, "mana_cost", ""),
        converted_mana_cost=getattr(card, "converted_mana_cost", 0),
        type=getattr(card, "type", ""),
        power=getattr(card, "power", ""),
        toughness=getattr(card, "toughness", ""),
        text=getattr(card, "text", ""),
        rarity=getattr(card, "rarity", ""),
        colors=getattr(card, "colors", []),
    )